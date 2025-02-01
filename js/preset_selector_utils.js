import { api } from "../../scripts/api.js";
import { app } from "../../scripts/app.js";
import * as utils from "./utils.js";
import { createComboToggleWidget } from "./custom_combobox.js";

/**
 * 서브폴더 위젯의 값을 복원합니다.
 * 값이 비어있거나 옵션에 없으면 기본값(옵션의 첫 번째 값 또는 "root")을 할당합니다.
 * @param {object} node - PresetSelectorV2 노드
 */
export function restoreSubfolderValue(node) {
  const subfolderWidget = utils.getWidget(node, "subfolder");
  if (!subfolderWidget) return;

  if (!subfolderWidget.value || !subfolderWidget.options.values.includes(subfolderWidget.value)) {
    const defaultValue =
      (subfolderWidget.options.values && subfolderWidget.options.values.length > 0)
        ? subfolderWidget.options.values[0]
        : "root";
    subfolderWidget.value = defaultValue;
    app.graph.setDirtyCanvas(true);
    console.log(`[PresetSelectorV2] Restored subfolder value to default: ${defaultValue}`);
  }
}

/**
 * /lora/list 엔드포인트를 호출하여 서브폴더 옵션과 프리셋 목록을 새로 갱신합니다.
 * 서브폴더 옵션은 data.subfolders, 프리셋 목록은 data.jsons (문자열 배열)로 반환됩니다.
 * 갱신 후 subfolder 위젯의 options와 value를 업데이트하고, updateWidgets()를 호출합니다.
 * @param {object} node - PresetSelectorV2 노드
 */
export async function refreshSubfolderList(node) {
  try {
    const subfolderWidget = utils.getWidget(node, "subfolder");
    if (!subfolderWidget) return;

    const response = await api.fetchApi("/lora/list");
    if (!response.ok) throw new Error("Failed to fetch LoRA file list");
    const data = await response.json();

    // 서브폴더 옵션 업데이트
    const subfolders = (data.subfolders && data.subfolders.length > 0) ? data.subfolders : ["none"];
    subfolderWidget.options.values = subfolders;
    if (!subfolderWidget.value || !subfolders.includes(subfolderWidget.value)) {
      subfolderWidget.value = subfolders[0];
    }
    app.graph.setDirtyCanvas(true);
    //console.log("[PresetSelectorV2] Subfolder list updated:", subfolders);

    // 프리셋 목록 업데이트
    await updateWidgets(node, subfolderWidget.value, false);
  } catch (error) {
    console.error("[PresetSelectorV2] Failed to refresh subfolders:", error);
    utils.customPrint(node, "ERROR", error.message);
  }
}

/**
 * 주어진 서브폴더에 해당하는 프리셋만 필터링합니다.
 * 여기서는 preset.path를 사용하며, subfolder와 일치하는 경로인 경우만 선택합니다.
 * @param {Array} allPresets - 전체 프리셋 배열 (각 preset 객체는 { path } 형태)
 * @param {string} subfolder - 선택된 서브폴더
 * @returns {Array} 필터링된 프리셋 배열
 */
export function filterPresets(allPresets, subfolder) {
  if (!Array.isArray(allPresets)) return [];
  const normalizedSub = subfolder.replace(/\\/g, "/");
  return allPresets.filter((preset) => {
    if (!preset || !preset.path || preset.path === "none") return false;
    const normPath = preset.path.replace(/\\/g, "/");
    if (normalizedSub === "root") {
      return normPath.split("/").length <= 2;
    }
    return normPath.startsWith(normalizedSub + "/");
  });
}

/**
 * 활성화된 custom 위젯(단일 선택)에서 선택된 preset의 전체 경로를 구성한 후,
 * SelectedPreset 위젯에 그 경로를 저장하고, 해당 경로의 프리셋 JSON 내용을 /lora/json API를 통해 로드하여
 * Result 위젯에 출력합니다.
 * 이 함수는 비동기로 동작합니다.
 * @param {object} node - PresetSelectorV2 노드
 * @returns {string} preset 경로 (전체 경로)
 */
export async function calculateActivePreset(node) {
  const subfolderWidget = utils.getWidget(node, "subfolder");
  const selectedPresetWidget = utils.getWidget(node, "SelectedPreset");
  const resultWidget = utils.getWidget(node, "Result");
  let presetPath = "";

  // 활성 custom 위젯 찾기 (단일 선택)
  for (const widget of node.widgets) {
    if (widget.type === "custom" && widget.isActive && widget.value !== "none") {
      // 전체 preset 경로 구성: subfolder + "/" + custom 위젯의 값(이 값은 파일 이름)
      presetPath = `${subfolderWidget.value}/${widget.value}`;
      break;
    }
  }

  // SelectedPreset 위젯에 전체 preset 경로 저장
  if (selectedPresetWidget) {
    selectedPresetWidget.value = presetPath;
  }

  // presetPath를 이용해 프리셋 JSON 내용을 로드합니다.
  try {
    const response = await api.fetchApi(`/lora/json?path=${encodeURIComponent(presetPath)}`);
    if (!response.ok) {
      const errData = await response.json();
      utils.customPrint(node, "ERROR", `Failed to load preset JSON: ${errData.error}`);
      if (resultWidget) {
        resultWidget.value = "";
      }
      return presetPath;
    }
    const data = await response.json();
    const jsonContent = JSON.stringify(data, null, 4);
    utils.customPrint(node, "SUCCESS", `${jsonContent}`);
    return presetPath;
  } catch (error) {
    utils.customPrint(node, "ERROR", error.message);
    if (resultWidget) {
      resultWidget.value = "";
    }
    return presetPath;
  }
}

/**
 * 노드의 custom 위젯들을 업데이트합니다.
 * - /lora/list 엔드포인트를 호출하여 서브폴더 옵션과 프리셋 목록을 최신으로 갱신합니다.
 * - data.jsons 배열을 이용해 각 프리셋 객체를 { path } 형태로 변환합니다.
 * - 필터링 후 각 preset.path에서 파일 이름(서브폴더 제외)을 추출하여 콤보 토글 위젯을 생성합니다.
 * - 출력 위젯("Result")는 calculateActivePreset()를 통해 업데이트합니다.
 * @param {object} node - PresetSelectorV2 노드
 * @param {string} subfolder - 현재 선택된 서브폴더
 * @param {boolean} isInitializing - 초기화 여부 (기존 상태 복원)
 */
export async function updateWidgets(node, subfolder, isInitializing = false) {
  try {
    restoreSubfolderValue(node);

    // 최신 데이터를 위해 /lora/list 호출
    const response = await api.fetchApi("/lora/list");
    if (!response.ok) throw new Error("Failed to fetch LoRA file list");
    const data = await response.json();

    // subfolder 위젯 업데이트
    const subfolderWidget = utils.getWidget(node, "subfolder");
    const subfolders = (data.subfolders && data.subfolders.length > 0) ? data.subfolders : ["none"];
    subfolderWidget.options.values = subfolders;
    if (!subfolderWidget.value || !subfolders.includes(subfolderWidget.value)) {
      subfolderWidget.value = subfolders[0];
    }
    app.graph.setDirtyCanvas(true);

    // 프리셋 목록은 data.jsons 배열에서 가져옴
    const allPresets = data.jsons.map(jsonFile => ({ path: jsonFile }));
    const filtered = filterPresets(allPresets, subfolder);
    const presetCount = Math.min(filtered.length, 20);
    // presetNames 배열: "none"과 필터링된 프리셋에서 파일 이름(서브폴더 제외)
    const presetNames = ["none", ...filtered.map(p => p.path.split("/").pop())];

    // 출력 위젯은 "Result" 사용
    const standardWidgets = node.widgets.filter(w => w.type !== "custom");
    const bypassWidget = utils.getWidget(node,"bypass");

    node.widgets = [...standardWidgets];

    // custom 위젯 생성 (단일 선택 방식)
    for (let i = 0; i < presetCount; i++) {
      const preset = filtered[i];
      if (!preset || preset.path === "none") continue;
      const presetFileName = preset.path.split("/").pop();

      const customW = createComboToggleWidget({
          name: `preset-combo-${i + 1}`,
          values: presetNames,
          defaultValue: presetFileName,
          // onChange 이벤트에 업데이트 함수 호출 추가 (비동기 처리)
          onChange: async (value) => {
            // 변경 후 Result 위젯 갱신
            await calculateActivePreset(node); // calculateActivePreset은 Result 위젯을 업데이트하도록 설계됨
            app.graph.setDirtyCanvas(true);
          },
          // onToggle 이벤트에도 동일하게 업데이트 함수 호출
          onToggle: async (isActive) => {
            if (bypassWidget?.value) return;
            if (isActive) {
              node.widgets.forEach(widget => {
                if (widget.type === "custom" && widget !== customW) {
                  widget.isActive = false;
                }
              });
            }
            await calculateActivePreset(node); // 선택된 프리셋이 변경될 때마다 Result 위젯 업데이트
            app.graph.setDirtyCanvas(true);
          }
        });

      // 단일 선택 방식: 현재 위젯 활성화 후 다른 위젯 비활성화
      customW.isActive = true;
      node.widgets.forEach(widget => {
        if (widget.type === "custom" && widget !== customW) {
          widget.isActive = false;
        }
      });
      node.widgets.push(customW);
    }

    // 📌 "Refresh" 버튼을 다시 비활성화 (false)
    const refreshWidget = utils.getWidget(node, "Refresh");
    if (refreshWidget) {
        refreshWidget.value = false;
    }

    // 최종적으로 출력 위젯("Result") 업데이트 (calculateActivePreset()가 async이므로 await)
    node.graph.setDirtyCanvas(true);
    app.graph.setDirtyCanvas(true);
  } catch (error) {
    console.error("[PresetSelectorV2] Failed to update widgets:", error);
  }
}

/**
 * bypass 상태 변경에 따라 custom 위젯들을 활성/비활성화 합니다.
 * @param {object} node - PresetSelectorV2 노드
 * @param {boolean} bypassValue - bypass 위젯의 값
 */
export function setBypassState(node, bypassValue) {
  node.widgets.forEach(widget => {
    if (widget.type === "custom") {
      widget.disabled = bypassValue;
    }
  });
  app.graph.setDirtyCanvas(true);
}

/**
 * Clear Preset 메뉴 옵션을 처리합니다.
 * 모든 custom 위젯의 값을 "none"으로 초기화하고, 출력 위젯("Result")와 SelectedPreset 위젯을 초기화합니다.
 * @param {object} node - PresetSelectorV2 노드
 */
export function clearPreset(node) {
  node.widgets.forEach(widget => {
    if (widget.type === "custom") {
      widget.value = "none";
      widget.isActive = false;
    }
  });
  const resultWidget = utils.getWidget(node, "Result");
  const selectedPresetWidget = utils.getWidget(node, "SelectedPreset");
  if (resultWidget) {
    resultWidget.value = "";
  }
  if (selectedPresetWidget) {
    selectedPresetWidget.value = "";
  }
  app.graph.setDirtyCanvas(true);
}
