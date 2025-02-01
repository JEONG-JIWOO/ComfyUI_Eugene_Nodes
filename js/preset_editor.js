import { app } from "../../scripts/app.js";
import * as utils from "./utils.js";  // 📌 utils.js도 통합 가져오기
import * as eugeneUtils from "./eugene_utils.js";  // 📌 모든 함수 통합 가져오기

app.registerExtension({
    name: "PresetEditor.extension",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // 📌 "PresetEditor" 노드인지 확인
        if (nodeType.comfyClass !== "PresetEditor") return;

        // 기존 onNodeCreated 유지
        const origOnNodeCreated = nodeType.prototype.onNodeCreated;

        nodeType.prototype.onNodeCreated = async function () {
            if (origOnNodeCreated) {
                origOnNodeCreated.apply(this, arguments);
            }

            // 📌 "Subfolder" 위젯에 콜백 연결
            const subfolderWidget = utils.getWidget(this, "Subfolder");
            if (subfolderWidget) {
                subfolderWidget.callback = () => eugeneUtils.updateLoraAndPresetList(this, subfolderWidget.value);
            }

            // 📌 "Select LoRA" 위젯에 콜백 연결 (선택 시 "Select Preset" 초기화)
            const loraWidget = utils.getWidget(this, "Select LoRA");
            if (loraWidget) {
                loraWidget.callback = () => eugeneUtils.handleLoraSelection(this);
            }

            // 📌 "Refresh" 버튼 콜백 연결
            const refreshButton = utils.getWidget(this, "Refresh");
            if (refreshButton) {
                refreshButton.callback = () => eugeneUtils.refreshSubfolderList(this);
            }

            // 📌 API 호출하여 초기 Subfolder 옵션 설정
            await eugeneUtils.refreshSubfolderList(this);
        };
    }
});
