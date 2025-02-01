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

/**
 * 📌 "Select Preset" 선택 시 해당 프리셋 정보를 API에서 가져와 위젯에 할당하는 함수
 * @param {object} node - PresetEditor 노드 객체
 */
export async function handlePresetSelection(node) {
    try {
        //console.log("[PresetEditor] Preset selected - Loading JSON data...");

        // 📌 "Select Preset"과 "Preset Name Suffix" 위젯 찾기
        const subfolderWidget = utils.getWidget(node, "Subfolder");
        const presetWidget = utils.getWidget(node, "Select Preset");
        const prefixWidget = utils.getWidget(node, "preset_name_prefix");
        const presetNameWidget = utils.getWidget(node, "preset_name");
        if (!presetWidget || !presetNameWidget) return;

        const selectedPreset = presetWidget.value;
        if (!selectedPreset || selectedPreset === "none") {
            console.log("[PresetEditor] No preset selected.");
            return;
        }

        // 📌 API 호출하여 JSON 데이터 가져오기
        const preset_path = `${subfolderWidget.value}/${selectedPreset}`
        const response = await api.fetchApi(`/lora/json?path=${encodeURIComponent(preset_path)}`);
        if (!response.ok) throw new Error("Failed to fetch preset JSON data");

        const data = await response.json();
        console.log("[PresetEditor] Loaded JSON Data:", data);

        // 📌 하위 호환 처리 (필드 매핑)
        const fieldMapping = {
            "lora_path": ["lora_path", "lora_name"],
            "strength_model": ["strength_model", "strength"],
            "strength_clip": ["strength_clip", "clip_strength"],
            "P1": ["P1", "prompt_positive"],
            "P2": ["P2", "sub_positive"],
            "P3": ["P3"],
            "N1": ["N1", "prompt_negative"],
            "N2": ["N2", "sub_negative"],
            "N3": ["N3"]
        };

        // 📌 위젯에 값 설정
        Object.entries(fieldMapping).forEach(([widgetName, jsonKeys]) => {
            const widget = utils.getWidget(node, widgetName);
            if (!widget) return;

            for (const key of jsonKeys) {
                if (data[key] !== undefined) {
                    widget.value = data[key];
                    break; // 첫 번째 유효한 값이 있으면 사용
                }
            }
        });


        // 📌 Windows 경로 정규화 (`\` → `/`)
        const loraWidget = utils.getWidget(node, "Select LoRA");
        let loraPath = (data.lora_path || data.lora_name || "").replace(/\\/g, "/");
        // 📌 subfolder 제외 (loraWidget.options.values은 subfolder 제외한 값)
        let loraFileName = loraPath.split("/").pop(); // 파일명만 추출
        // 📌 combobox에 있는 값이면 선택, 없으면 "none"
        if (loraWidget.options.values.includes(loraFileName)) {
            loraWidget.value = loraFileName; // combobox 값으로 설정
        } else {
            console.warn("[PresetEditor] LoRA file not found in options, setting to 'none'.");
            loraWidget.value = "none"; // 유효하지 않으면 "none" 설정
        }

        // 📌 "preset_name" 설정 (하위호환 고려)
        let presetName = selectedPreset.replace(".json", ""); // 기본적으로 파일 이름에서 확장자 제거

        if (data.nickname && typeof data.nickname === "string" && data.nickname.trim().length > 0) {
            presetName = data.nickname; // nickname 필드가 있으면 우선 사용
        }

        // 📌 Prefix 제거 (있는 경우)
        if (prefixWidget && prefixWidget.value && presetName.startsWith(prefixWidget.value)) {
            presetName = presetName.slice(prefixWidget.value.length); // prefix 부분 제거
        }

        presetNameWidget.value = presetName; // 최종 preset_name 설정

        // 📌 UI 업데이트 반영
        app.graph.setDirtyCanvas(true);
        utils.customPrint(node, "Success", `Load Json:\n${JSON.stringify(data, null, 4)}`);

    } catch (error) {
        console.error("[PresetEditor] Failed to load preset:", error);
        utils.customPrint(node, "ERROR", error.message);
    }
}

export async function handleCivitaiSelection(node) {
    try {
        // 📌 "Select LoRA" 위젯에서 선택된 파일명을 가져옴
        const loraWidget = utils.getWidget(node, "Select LoRA");
        if (!loraWidget) return;
        const selectedLoRA = loraWidget.value;
        if (!selectedLoRA || selectedLoRA === "none") {
            console.warn("[PresetEditor] No LoRA file selected.");
            return;
        }

        // 📌 "Subfolder" 위젯에서 현재 서브폴더명을 가져옴
        const subfolderWidget = utils.getWidget(node, "Subfolder");
        if (!subfolderWidget) return;
        const subfolder = subfolderWidget.value;

        // 📌 파일 경로 구성 (예: "SD1.5/enhance.safetensors")
        const filePath = `${subfolder}/${selectedLoRA}`;

        // 📌 기존 API를 통해 선택된 파일의 SHA256 해시 가져오기
        const hashResponse = await api.fetchApi(`/lora/hash?path=${encodeURIComponent(filePath)}`);
        if (!hashResponse.ok) throw new Error("Failed to fetch file hash");
        const hashData = await hashResponse.json();
        if (hashData.error) throw new Error(hashData.error);
        const fileHash = hashData.hash;

        // 📌 civitai API 호출 (SHA256 해시를 이용)
        const civitaiResponse = await fetch(`https://civitai.com/api/v1/model-versions/by-hash/${fileHash}`);
        if (!civitaiResponse.ok) throw new Error("Failed to fetch civitai data");
        const civitaiData = await civitaiResponse.json();

        // 📌 "P1" 위젯에 trainedWords 할당 (배열이면 콤마로 연결)
        const p1Widget = utils.getWidget(node, "P1");
        if (p1Widget) {
            p1Widget.value = Array.isArray(civitaiData.trainedWords)
                ? civitaiData.trainedWords.join(", ")
                : "";
        }

        // 📌 "P2" 위젯에 첫 번째 이미지의 meta.prompt 할당
        const p2Widget = utils.getWidget(node, "P2");
        if (p2Widget) {
            if (civitaiData.images &&
                civitaiData.images.length > 0 &&
                civitaiData.images[0].meta &&
                civitaiData.images[0].meta.prompt) {
                //p2Widget.value = civitaiData.images[0].meta.prompt;
                p2Widget.value = "";
            } else {
                p2Widget.value = "";
            }
        }

        // 📌 추가: "P3", "N1", "N2", "N3" 공백 값 할당
        const p3Widget = utils.getWidget(node, "P3");
        if (p3Widget) p3Widget.value = "";

        const n1Widget = utils.getWidget(node, "N1");
        if (n1Widget) n1Widget.value = "";

        const n2Widget = utils.getWidget(node, "N2");
        if (n2Widget) n2Widget.value = "";

        const n3Widget = utils.getWidget(node, "N3");
        if (n3Widget) n3Widget.value = "";

        // 📌 "preset_name_prefix": 값이 비어있다면 baseModel 할당
        const prefixWidget = utils.getWidget(node, "preset_name_prefix");
        if (prefixWidget && !prefixWidget.value) {
            prefixWidget.value = civitaiData.baseModel || "";
        }

        // 📌 "preset_name" 위젯에 model.name 할당 (civitaiData.model.name)
        const presetNameWidget = utils.getWidget(node, "preset_name");
        if (presetNameWidget) {
            presetNameWidget.value = (civitaiData.model && civitaiData.model.name) ? civitaiData.model.name : "";
        }

        // 📌 "Result" 위젯에 civitai 접속 링크 할당 (예: https://civitai.com/models/706978)
        const resultWidget = utils.getWidget(node, "Result");
        if (resultWidget) {
            const modelId = civitaiData.modelId;
            resultWidget.value = `https://civitai.com/models/${modelId}`;
        }

        const linkWidget = node.widgets.find(w => w.name === "CivitaiLinkButton");
        if (linkWidget) {
          const modelId = civitaiData.modelId;
          linkWidget.value = `https://civitai.com/models/${modelId}`;
        }

        // 📌 "civitaiButton 버튼을 다시 비활성화 (false)
        const civitaiButton = utils.getWidget(node, "Load From Civitai");
        if (civitaiButton) {
            civitaiButton.value = false;
            //node.graph.setDirtyCanvas(true);
        }

        // 📌 UI 업데이트
        app.graph.setDirtyCanvas(true);
    } catch (error) {
        console.error("[PresetEditor] Failed to load civitai data:", error);
        utils.customPrint(node, "ERROR", error.message);
    }
}
