import { app } from "../../scripts/app.js";
import * as utils from "./utils.js";               // 공통 유틸 (getWidget, customPrint 등)
import { createComboToggleWidget } from "./custom_widget.js";
import * as presetSelectorUtils from "./preset_selector_utils.js"; // 모든 로직은 이 파일에서 처리

// PresetSelectorV2 노드 등록
app.registerExtension({
  name: "PresetSelectorV2.extension",

  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    // 노드 타입이 "LoraPresetSelectorV2" 인 경우에만 처리
    if (nodeType.comfyClass !== "LoraPresetSelectorV2") return;

    const origOnNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = async function () {
      if (origOnNodeCreated) {
        origOnNodeCreated.apply(this, arguments);
      }

      // 필수 위젯 (subfolder, refresh, bypass) 찾기
      const subfolderWidget = utils.getWidget(this, "subfolder");
      const refreshWidget = utils.getWidget(this, "Refresh"); // Refresh 위젯 이름: "Refresh"
      const bypassWidget = utils.getWidget(this, "bypass");

      if (!subfolderWidget || !refreshWidget || !bypassWidget) {
        console.error("[PresetSelectorV2] Required widgets not found!");
        return;
      }

      // 서브폴더 선택 시, 노드 제목 업데이트 및 위젯 갱신 (custom 위젯 이름에는 subfolder 정보 제외)
      subfolderWidget.callback = async () => {
        this.title = `Group: ${subfolderWidget.value}`;
        await presetSelectorUtils.updateWidgets(this, subfolderWidget.value, false);
      };

      // "Refresh" 버튼 콜백: /lora/list 엔드포인트를 통해 subfolder 위젯의 value와 options를 업데이트
      refreshWidget.callback = async () => {
        await presetSelectorUtils.refreshSubfolderList(this);
        app.graph.setDirtyCanvas(true);
      };

      // bypass 위젯 콜백: bypass 상태에 따라 custom 위젯들 활성/비활성화
      bypassWidget.callback = () => {
        presetSelectorUtils.setBypassState(this, bypassWidget.value);
      };

        // 한 번만 업데이트 실행
        await presetSelectorUtils.updateWidgets(this, subfolderWidget.value, true);
        this.graph.setDirtyCanvas(true);
        app.graph.setDirtyCanvas(true);

      // 그래프 로드 완료 후, 일정 시간 지연(1초) 후 복원 시도
      setTimeout(() => {
        presetSelectorUtils.restoreSubfolderValue(this);
        presetSelectorUtils.updateWidgets(this, subfolderWidget.value, true);
        this.graph.setDirtyCanvas(true);
        app.graph.setDirtyCanvas(true);
      }, 1000);
    };

    // serialize: 위젯 값과 custom 위젯 상태 저장
    const origSerialize = nodeType.prototype.serialize;
    nodeType.prototype.serialize = function () {
      const data = origSerialize ? origSerialize.apply(this) : {};
      data.widgets_values = this.widgets.map(w => w.value);
      data.custom_widget_states = this.widgets
        .filter(w => w.type === "custom")
        .map(w => ({
          value: w.value,
          isActive: w.isActive
        }));
      return data;
    };

    // configure: 저장된 위젯 상태 복원
    const origConfigure = nodeType.prototype.configure;
    nodeType.prototype.configure = function (info) {
      if (origConfigure) {
        origConfigure.apply(this, arguments);
      }
      if (info.widgets_values) {
        this.widgets_values = info.widgets_values;
      }
      if (info.custom_widget_states) {
        const customWidgets = this.widgets.filter(w => w.type === "custom");
        info.custom_widget_states.forEach((state, index) => {
          if (customWidgets[index]) {
            customWidgets[index].value = state.value;
            customWidgets[index].isActive = state.isActive;
          }
        });
      }
    };
  }
});
