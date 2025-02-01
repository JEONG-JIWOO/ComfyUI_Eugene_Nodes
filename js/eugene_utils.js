// 📌 파일: extensions/utils/eugene_utils.js
import { api } from "../../scripts/api.js";
import { app } from "../../scripts/app.js";
import * as utils from "./utils.js";  // 📌 utils.js도 통합 가져오기

/**
 * 📌 Subfolder 목록을 다시 불러와서 업데이트하는 함수
 * @param {object} node - PresetEditor 노드 객체
 */
export async function refreshSubfolderList(node) {
    try {
        //console.log("[PresetEditor] Refreshing subfolder list...");

        // 📌 위젯 찾기
        const subfolderWidget = utils.getWidget(node, "Subfolder");
        const refreshWidget = utils.getWidget(node, "Refresh");

        if (!subfolderWidget) return;

        // 📌 "Result" 필드에 INFO 로그 추가
        utils.customPrint(node, "INFO", "Refreshing LoRA subfolder list...");

        // 📌 LoRA 폴더 리스트 가져오기
        const response = await api.fetchApi("/lora/list");
        if (!response.ok) throw new Error("Failed to fetch LoRA subfolders");
        const data = await response.json();

        // 📌 API 응답에서 subfolders 리스트 추출 (기본값 "none" 포함)
        const subfolders = data.subfolders.length > 0 ? data.subfolders : ["none"];

        // 📌 Subfolder 옵션 업데이트
        subfolderWidget.options.values = subfolders;
        app.graph.setDirtyCanvas(true);  // UI 업데이트

        //console.log("[PresetEditor] Subfolder list updated:", subfolders);

        // 📌 "Result" 필드에 SUCCESS 로그 추가
        utils.customPrint(node, "SUCCESS", "LoRA subfolder list updated!");

        // 📌 "Refresh" 버튼을 다시 비활성화 (false)
        if (refreshWidget) {
            refreshWidget.value = false;
        }

        app.graph.setDirtyCanvas(true);  // UI 업데이트

    } catch (error) {
        console.error("[PresetEditor] Failed to refresh subfolders:", error);
        utils.customPrint(node, "ERROR", error.message);
    }
}

/**
 * 📌 "Select LoRA" 선택 시 "Select Preset"을 자동으로 초기화하는 함수
 * @param {object} node - PresetEditor 노드 객체
 */
export function handleLoraSelection(node) {
    //console.log("[PresetEditor] LoRA selected - Resetting Preset selection...");

    // 📌 "Select Preset" 위젯 찾기
    const presetWidget = utils.getWidget(node, "Select Preset");
    if (!presetWidget) return;

    // 📌 "Select Preset" 값을 "none"으로 초기화
    presetWidget.value = "none";
    app.graph.setDirtyCanvas(true);  // UI 업데이트
}

/**
 * 📌 Subfolder를 기반으로 Select LoRA 및 Select Preset 콤보박스 업데이트
 * @param {object} node - PresetEditor 노드 객체
 * @param {string} subfolder - 선택된 Subfolder 값
 */
export async function updateLoraAndPresetList(node, subfolder) {
    try {
        //console.log(`[PresetEditor] Updating LoRA & Preset list for subfolder: ${subfolder}`);

        // 📌 위젯 찾기
        const loraWidget = utils.getWidget(node, "Select LoRA");
        const presetWidget = utils.getWidget(node, "Select Preset");
        if (!loraWidget || !presetWidget) return;

        // 📌 API 호출하여 safetensors 및 json 파일 필터링
        const response = await api.fetchApi("/lora/list");
        if (!response.ok) throw new Error("Failed to fetch LoRA file list");
        const data = await response.json();

        // 📌 선택된 subfolder에 속하는 파일 필터링
        const safetensors = data.safetensors.filter(file => file.startsWith(subfolder));
        const jsons = data.jsons.filter(file => file.startsWith(subfolder));

        // 📌 파일명만 추출 (subfolder 제거)
        const loraFiles = safetensors.map(file => file.replace(subfolder + "/", ""));
        const presetFiles = jsons.map(file => file.replace(subfolder + "/", ""));

        // 📌 Select LoRA & Select Preset 목록 업데이트
        loraWidget.options.values = loraFiles.length > 0 ? loraFiles : ["none"];
        presetWidget.options.values = presetFiles.length > 0 ? presetFiles : ["none"];

        app.graph.setDirtyCanvas(true);  // UI 업데이트
        //console.log("[PresetEditor] Updated LoRA & Preset lists:", { loraFiles, presetFiles });

    } catch (error) {
        console.error("[PresetEditor] Failed to update LoRA & Preset lists:", error);
    }
}
