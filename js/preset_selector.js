import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
  name: "LoraPresetSelector.extension",

  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    // LoraPresetSelector 노드에만 적용
    if (nodeType.comfyClass !== "LoraPresetSelector") {
      return;
    }

    let cachedPresets = null;

    /**
     * /lora_presets/refresh -> 프리셋 갱신
     */
    async function refreshPresets() {
      try {
        const response = await api.fetchApi("/lora_presets/refresh");
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        if (!data || !data.presets) {
          throw new Error("[LoraPresetSelector] Invalid response format");
        }
        cachedPresets = data.presets;
        console.log("[LoraPresetSelector] Refreshed presets:", cachedPresets);
        return data;
      } catch (error) {
        console.error("[LoraPresetSelector] Failed to refresh presets:", error);
        return null;
      }
    }

    /**
     * /lora_presets -> 프리셋 목록 (캐시)
     */
    async function getPresets() {
      if (cachedPresets) return cachedPresets;
      try {
        const response = await api.fetchApi("/lora_presets");
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        if (!data || !data.presets) {
          throw new Error("[LoraPresetSelector] Invalid response format");
        }
        cachedPresets = data.presets;
        console.log("[LoraPresetSelector] All presets from server:", cachedPresets);
        return cachedPresets;
      } catch (error) {
        console.error("[LoraPresetSelector] Failed to fetch presets:", error);
        return [];
      }
    }

    /**
     * 단순히 UI에 표시할 목록을 만드는 정도로만 사용.
     * (유효성 체크를 원치 않으므로, "목록에 없으면 none" 같은 처리는 하지 않음)
     */
    function filterPresets(allPresets, subfolder) {
      // 여기서는 간단히 "subfolder"에 맞춰 경로를 골라낼 뿐,
      // 최종 preset 값 덮어쓰지 않음
      if (!Array.isArray(allPresets)) return [];
      const normalizedSub = subfolder.replace(/\\/g, "/");

      return allPresets.filter((preset) => {
        if (!preset || preset.path === "none") return true;
        const normPath = preset.path.replace(/\\/g, "/");
        if (normalizedSub === "root") {
          // root: 슬래시 1회 이하
          return normPath.split("/").length <= 2;
        }
        return normPath.startsWith(normalizedSub + "/");
      });
    }

    // 기존 onNodeCreated 백업
    const origOnNodeCreated = nodeType.prototype.onNodeCreated;

    // 새 onNodeCreated
    nodeType.prototype.onNodeCreated = async function () {
      if (origOnNodeCreated) {
        origOnNodeCreated.apply(this, arguments);
      }

      // 워크플로우 로드 시점에 담기는 데이터
      const savedData = this.data ?? this.properties ?? nodeData ?? {};
      console.log("[LoraPresetSelector] onNodeCreated -> savedData:", savedData);

      // 위젯 찾기
      const subfolderWidget = this.widgets.find(w => w.name === "subfolder");
      const presetWidget = this.widgets.find(w => w.name === "preset");
      const refreshWidget = this.widgets.find(w => w.name === "refresh");

      if (!subfolderWidget || !presetWidget) {
        console.warn("[LoraPresetSelector] Required widgets not found!");
        return;
      }

      // refresh
      if (refreshWidget) {
        refreshWidget.callback = async () => {
          if (refreshWidget.value) {
            console.log("[LoraPresetSelector] Refreshing presets...");
            const data = await refreshPresets();
            if (data) {
              cachedPresets = null;
              // subfolder 콜백 재실행
              await subfolderWidget.callback();
            }
            refreshWidget.value = false;
            app.graph.setDirtyCanvas(true);
          }
        };
      }

      // 사용자 직접 preset 변경 -> 저장
      presetWidget.callback = () => {
        const newPreset = presetWidget.value;
        console.log("[LoraPresetSelector] User changed preset to:", newPreset);

        // 노드 이름 변경
        if (newPreset && typeof newPreset === "string" && newPreset !== "none") {
          this.title = newPreset; // 노드 이름 변경
          console.log("[LoraPresetSelector] Node title updated to:", newPreset);
        }

        // 워크플로우 저장
        app.graph.setDirtyCanvas(true);
      };


      // subfolder 변경 콜백
      // (필터 목록을 UI에 표시하기만 하고,
      //  지금은 "유효성 체크"를 안 해서 기존 preset을 덮어쓰지 않음)
      const origSubfolderCallback = subfolderWidget.callback;
      subfolderWidget.callback = async () => {
        if (typeof origSubfolderCallback === "function") {
          origSubfolderCallback.call(subfolderWidget);
        }

        const subfolder = subfolderWidget.value;
        console.log("[LoraPresetSelector] Subfolder changed ->", subfolder);

        // UI용 목록만 업데이트
        const all = await getPresets();
        const filtered = filterPresets(all, subfolder);
        const presetNames = filtered.map(p => p.display_name || "none");

        // 중복제거 + "none"을 맨 앞에 추가 (UI 표시용)
        const finalList = Array.from(new Set(["none", ...presetNames]));

        // 콤보 목록 갱신
        presetWidget.options.values = finalList;
        // ★ 기존에 선택된 presetWidget.value를 **절대 덮어쓰지 않음**
        // -> "유효성 체크" 없이 그냥 둠

        app.graph.setDirtyCanvas(true);
      };

      // (1) **저장된 subfolder** 가 있으면 무조건 덮어씀
      const savedSubfolder = savedData.properties?.subfolder;
      if (savedSubfolder !== undefined) {
        console.log("[LoraPresetSelector] Force set subfolder to saved:", savedSubfolder);
        subfolderWidget.value = savedSubfolder;
      }
      // (2) **저장된 preset** 이 있으면 무조건 덮어씀
      const savedPreset = savedData.properties?.preset;
      if (savedPreset !== undefined) {
        console.log("[LoraPresetSelector] Force set preset to saved:", savedPreset);
        presetWidget.value = savedPreset;
      }

      // subfolder 콜백 1회 호출 -> UI 목록만 업데이트하고, 현재 preset은 그대로 둠
      await subfolderWidget.callback();
    };
  }
});
