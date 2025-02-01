import { app } from "../../scripts/app.js";
import * as utils from "./utils.js";  // 📌 utils.js도 통합 가져오기
import * as eugeneUtils from "./eugene_utils.js";  // 📌 모든 함수 통합 가져오기
import {createHyperlinkWidget} from "./custom_widget.js";  // 📌 모든 함수 통합 가져오기

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

            // 📌 "Select Preset" 위젯에 콜백 연결 (선택 시 JSON 데이터 로드)
            const presetWidget = utils.getWidget(this, "Select Preset");
            if (presetWidget) {
                presetWidget.callback = () => eugeneUtils.handlePresetSelection(this);
            }

             // 📌 "Load From Preset" 버튼 콜백 연결
            const  presetButton = utils.getWidget(this, "Load From Preset");
            if (presetButton) {
                presetButton.callback = () => eugeneUtils.handlePresetSelection(this);
            }

             // 📌 "Load From civitai" 버튼 콜백 연결
            const civitaiButton = utils.getWidget(this, "Load From Civitai");
            if (civitaiButton) {
                civitaiButton.callback = () => eugeneUtils.handleCivitaiSelection(this);
            }

            // 📌 Save JSON 버튼에 콜백 연결
            const saveJSONWidget = utils.getWidget(this, "Save JSON");
            if (saveJSONWidget) {
                saveJSONWidget.callback = () => eugeneUtils.savePresetJson(this);
            }

            // 📌 "Refresh" 버튼 콜백 연결
            const refreshButton = utils.getWidget(this, "Refresh");
            if (refreshButton) {
                refreshButton.callback = () => eugeneUtils.refreshSubfolderList(this);
            }

            // 📌 Civitai 링크 커스텀 하이퍼링크 추가.
            this.widgets.push(createHyperlinkWidget({
               name: "CivitaiLinkButton",
               defaultUrl: "", // 초기에는 빈 문자열로 시작
               onClick: (url) => {
                 console.log("Link clicked:", url);
               }
            }));

            // 📌 API 호출하여 초기 Subfolder 옵션 설정
            await eugeneUtils.refreshSubfolderList(this);
        };
    }
});
