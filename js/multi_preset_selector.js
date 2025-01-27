import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { createComboToggleWidget } from "./custom_combobox.js";

app.registerExtension({
  name: "LoraMultiPresetSelector.extension",
  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    if (nodeType.comfyClass !== "LoraMultiPresetSelector") return;

    let cachedPresets = null;

    async function refreshPresets() {
      try {
        const response = await api.fetchApi("/lora_presets/refresh");
        const data = await response.json();
        cachedPresets = data.presets;
        return data;
      } catch (error) {
        console.error("[LoraMultiPresetSelector] Failed to refresh presets:", error);
        return null;
      }
    }

    async function getPresets() {
      if (cachedPresets) return cachedPresets;
      try {
        const response = await api.fetchApi("/lora_presets");
        const data = await response.json();
        cachedPresets = data.presets;
        return cachedPresets;
      } catch (error) {
        console.error("[LoraMultiPresetSelector] Failed to fetch presets:", error);
        return [];
      }
    }

    function filterPresets(allPresets, subfolder) {
      if (!Array.isArray(allPresets)) return [];
      const normalizedSub = subfolder.replace(/\\/g, "/");

      return allPresets.filter((preset) => {
        if (!preset || preset.display_name === "none") return true;
        const normPath = preset.path.replace(/\\/g, "/");
        if (normalizedSub === "root") {
          return normPath.split("/").length <= 2;
        }
        return normPath.startsWith(normalizedSub + "/");
      });
    }

    function calculateActivePresets(node) {
      const activePresets = [];
      node.widgets.forEach(widget => {
        if (widget.type === "custom" && widget.isActive && widget.value !== "none") {
          activePresets.push(widget.value); // display_name 저장
        }
      });
      return JSON.stringify(activePresets);
    }

    // 위젯 업데이트 함수
    async function updateWidgets(node, subfolder, isInitializing = false) {
      // 기존 위젯 상태 보존
      const standardWidgets = node.widgets.filter(w => w.type !== "custom");
      const outputWidget = standardWidgets.find(w => w.name === "output_loras");
      const bypassWidget = standardWidgets.find(w => w.name === "bypass");
      const subfolderWidget = standardWidgets.find(w => w.name === "subfolder");

      if (!outputWidget) {
        console.error("[LoraMultiPresetSelector] Output widget not found!");
        return;
      }

      // 저장된 상태에서 subfolder 확인
      let currentSubfolder = subfolder;

      // 복원 시도
      if (isInitializing) {
        if( !node){
            return;
        }
        console.log("Initializing with saved values:", node.widgets_values);
        const savedSubfolder = node.widgets_values[
            node.widgets.findIndex(w => w.name === "subfolder")
        ];

        if (savedSubfolder) {
            currentSubfolder = savedSubfolder;
            if (subfolderWidget) {
                subfolderWidget.value = currentSubfolder;
            }
            console.log("Restored subfolder:", currentSubfolder);
        }
    }

      // 프리셋 필터링
      const all = await getPresets();
      const filtered = filterPresets(all, currentSubfolder);
      const presetCount = Math.min(filtered.length, 20);
      const presetNames = ["none", ...filtered.map(p => p.display_name)];

      // 현재 활성화된 display_name 목록
      let activeDisplayNames = [];
      try {
        activeDisplayNames = JSON.parse(outputWidget.value || "[]");
        console.log("Active display names:", activeDisplayNames);
      } catch (e) {
        console.error("Failed to parse output_loras:", e);
      }

      // 위젯 목록 재구성
      node.widgets = [...standardWidgets];

      // 새 커스텀 위젯 추가
      for (let i = 0; i < presetCount; i++) {
        const preset = filtered[i];
        if (!preset) continue;
        if (preset.path == "none") continue;

        const displayName = preset.display_name || "none";

        const customW = createComboToggleWidget({
          name: `preset-combo-${i + 1}`,
          values: presetNames,
          defaultValue: displayName,
          onChange: (value) => {
            if (bypassWidget?.value) return;
            outputWidget.value = calculateActivePresets(node);
            app.graph.setDirtyCanvas(true);
          },
          onToggle: (isActive) => {
            if (bypassWidget?.value) return;
            outputWidget.value = calculateActivePresets(node);
            app.graph.setDirtyCanvas(true);
          }
        });

        // 이전 상태 복원
        if (activeDisplayNames.includes(displayName)) {
          customW.isActive = true;
        }

        node.widgets.push(customW);
      }

      // 활성화된 프리셋 목록 업데이트
      if (!isInitializing) {
        outputWidget.value = calculateActivePresets(node);
      }
      app.graph.setDirtyCanvas(true);
    }

    const origGetExtraMenuOptions = nodeType.prototype.getExtraMenuOptions;
    nodeType.prototype.getExtraMenuOptions = function(_, options) {
      if (origGetExtraMenuOptions) {
        origGetExtraMenuOptions.apply(this, arguments);
      }

      options.unshift({
        content: "Clear All Presets",
        callback: () => {
          // 모든 커스텀 위젯 리셋
          this.widgets.forEach(widget => {
            if (widget.type === "custom") {
              widget.value = "none";
              widget.isActive = false;
            }
          });

          // 출력값 초기화
          const outputWidget = this.widgets.find(w => w.name === "output_loras");
          if (outputWidget) {
            outputWidget.value = "[]";
          }

          app.graph.setDirtyCanvas(true);
        }
      });
    };

    const origOnNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = async function() {
        try {
            if (origOnNodeCreated) {
                origOnNodeCreated.apply(this, arguments);
            }

            const subfolderWidget = this.widgets.find(w => w.name === "subfolder");
            const refreshWidget = this.widgets.find(w => w.name === "refresh");
            const bypassWidget = this.widgets.find(w => w.name === "bypass");

            if (!subfolderWidget || !refreshWidget || !bypassWidget) {
                console.error("[LoraMultiPresetSelector] Required widgets not found!");
                return;
            }

            // Subfolder change callback 설정
            const origSubfolderCallback = subfolderWidget.callback;
            subfolderWidget.callback = async () => {
                if (typeof origSubfolderCallback === "function") {
                    origSubfolderCallback.call(subfolderWidget);
                }

                const subfolder = subfolderWidget.value;
                this.title = `Group: ${subfolder}`;
                await updateWidgets(this, subfolder, false);
            };

            // Refresh callback 설정
            refreshWidget.callback = async () => {
                if (refreshWidget.value) {
                    const data = await refreshPresets();
                    if (data) {
                        cachedPresets = null;
                        await subfolderWidget.callback();
                    }
                    refreshWidget.value = false;
                    app.graph.setDirtyCanvas(true);
                }
            };

            // Bypass callback 설정
            bypassWidget.callback = () => {
                this.widgets.forEach(widget => {
                    if (widget.type === "custom") {
                        widget.disabled = bypassWidget.value;
                    }
                });
                app.graph.setDirtyCanvas(true);
            };


            // node가 준비될 때까지 500ms마다 체크
            const waitForNode = () => {
                if (!this || !this.widgets_values) {
                    setTimeout(waitForNode, 500);
                    console.log("[LoraMultiPresetSelector] Waiting for node initialization...");
                    return;
                }

                console.log("[LoraMultiPresetSelector] Node ready, updating widgets...");
                updateWidgets(this, subfolderWidget.value, true);
                app.graph.setDirtyCanvas(true);
            };

            waitForNode();
        } catch (error) {
            console.error("[LoraMultiPresetSelector] Error in onNodeCreated:", error);
        }
    };

    // 상태 저장
    const origSerialize = nodeType.prototype.serialize;
    nodeType.prototype.serialize = function() {
        const data = origSerialize ? origSerialize.apply(this) : {};

        // 실제 위젯 값들을 저장
        data.widgets_values = this.widgets.map(w => w.value);

        // 커스텀 위젯의 활성화 상태도 저장
        data.custom_widget_states = this.widgets
            .filter(w => w.type === "custom")
            .map(w => ({
                value: w.value,
                isActive: w.isActive
            }));

        return data;
    };

    const origConfigure = nodeType.prototype.configure;
    nodeType.prototype.configure = function(info) {
        if (origConfigure) {
            origConfigure.apply(this, arguments);
        }

        // 기본 위젯 값 복원
        if (info.widgets_values) {
            this.widgets_values = info.widgets_values;
        }

        // 커스텀 위젯 상태 복원
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