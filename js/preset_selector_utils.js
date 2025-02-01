import { api } from "../../scripts/api.js";
import { app } from "../../scripts/app.js";
import * as utils from "./utils.js";
import { createComboToggleWidget } from "./custom_combobox.js";

/**
 * 서브폴더 위젯의 값을 복원합니다.
 * 만약 위젯의 값이 비어있거나, 옵션에 포함되지 않는다면 기본값(옵션의 첫 번째 값 또는 "root")을 할당합니다.
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
 * 서브폴더 옵션은 data.subfolders, 프리셋 목록은 data.jsons (각각 문자열 배열)로 반환됩니다.
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
    console.log("[PresetSelectorV2] Subfolder list updated:", subfolders);

    // 프리셋 목록 업데이트 (아래 updateWidgets()에서도 /lora/list를 호출하지만 refresh 시에도 함께 호출할 수 있음)
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
 * 활성화된 custom 위젯들의 preset 값(파일 이름, 즉 서브폴더 제외한 이름)을 JSON 문자열로 계산하여 반환합니다.
 * @param {object} node - PresetSelectorV2 노드
 * @returns {string} JSON 문자열
 */
export function calculateActivePreset(node) {
  const subfolderWidget = utils.getWidget(node, "subfolder");
  for (const widget of node.widgets) {
    if (widget.type === "custom" && widget.isActive && widget.value !== "none") {
        return `${subfolderWidget.value}/${widget.value}`
    }
  }
  return "";
}

/**
 * 노드의 custom 위젯들을 업데이트합니다.
 * - /lora/list 엔드포인트를 호출하여 서브폴더 옵션과 프리셋 목록을 최신으로 갱신합니다.
 * - data.jsons 배열을 이용하여 각 프리셋 객체를 { path } 형태로 변환합니다.
 * - filtered 프리셋의 preset.path에서 파일 이름만 추출하여 콤보 토글 위젯을 생성합니다.
 * - 출력 위젯(Result)의 값은 calculateActivePreset() 함수를 통해 업데이트합니다.
 * @param {object} node - PresetSelectorV2 노드
 * @param {string} subfolder - 현재 선택된 서브폴더
 * @param {boolean} isInitializing - 초기화 여부 (기존 상태 복원)
 */
export async function updateWidgets(node, subfolder, isInitializing = false) {
  try {
    // 먼저 subfolder 위젯 값을 복원
    restoreSubfolderValue(node);

    // 서브폴더 옵션을 최신화하기 위해 /lora/list 호출 (항상 새 데이터를 가져옴)
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

    // 프리셋 목록은 data.jsons 배열에서 가져옵니다.
    const allPresets = data.jsons.map(jsonFile => ({ path: jsonFile }));
    const filtered = filterPresets(allPresets, subfolder);
    const presetCount = Math.min(filtered.length, 20);
    // presetNames 배열은 "none"과 filtered 프리셋에서 파일 이름(서브폴더 제외)으로 구성됩니다.
    const presetNames = ["none", ...filtered.map(p => p.path.split("/").pop())];

    // 출력 위젯 이름은 "Result"로 사용합니다.
    const standardWidgets = node.widgets.filter(w => w.type !== "custom");
    const outputWidget = standardWidgets.find(w => w.name === "SelectedPreset");
    const bypassWidget = standardWidgets.find(w => w.name === "bypass");

    if (!outputWidget) {
      console.error("[PresetSelectorV2] Result widget not found!");
      return;
    }

    let activeDisplayNames = [];
    try {
      activeDisplayNames = JSON.parse(outputWidget.value || "");
    } catch (e) {
      console.error("Failed to parse Result value:", e);
    }

    // 기존 standard 위젯들은 그대로 유지
    node.widgets = [...standardWidgets];

    // custom 위젯들을 새로 생성 (단일 선택 방식)
    for (let i = 0; i < presetCount; i++) {
      const preset = filtered[i];
      if (!preset || preset.path === "none") continue;
      const presetFileName = preset.path.split("/").pop();

      const customW = createComboToggleWidget({
        name: `preset-combo-${i + 1}`,
        values: presetNames,
        defaultValue: presetFileName,
        onChange: (value) => {
          if (bypassWidget?.value) return;
          outputWidget.value = calculateActivePreset(node);
          app.graph.setDirtyCanvas(true);
        },
        onToggle: (isActive) => {
          if (bypassWidget?.value) return;
          if (isActive) {
            node.widgets.forEach(widget => {
              if (widget.type === "custom" && widget !== customW) {
                widget.isActive = false;
              }
            });
          }
          outputWidget.value = calculateActivePreset(node);
          app.graph.setDirtyCanvas(true);
        }
      });

      if (activeDisplayNames.includes(presetFileName)) {
        customW.isActive = true;
        node.widgets.forEach(widget => {
          if (widget.type === "custom" && widget !== customW) {
            widget.isActive = false;
          }
        });
      }
      node.widgets.push(customW);
    }

    if (!isInitializing) {
      outputWidget.value = calculateActivePreset(node);
    }
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
