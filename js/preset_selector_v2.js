import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { createComboToggleWidget } from "./custom_combobox.js";

app.registerExtension({
  name: "LoraPresetSelectorV2.extension",
  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    if (nodeType.comfyClass !== "LoraPresetSelectorV2") return;

    let cachedPresets = null;

    async function refreshPresets() {
      try {
        const response = await api.fetchApi("/lora_presets/refresh");
        const data = await response.json();
        cachedPresets = data.presets;
        return data;
      } catch (error) {
        console.error("[PresetSelectorV2] Failed to refresh presets:", error);
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
        console.error("[PresetSelectorV2] Failed to fetch presets:", error);
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

    function calculateActivePreset(node) {
      const activePreset = [];
      for (const widget of node.widgets) {
        if (widget.type === "custom" && widget.isActive && widget.value !== "none") {
          activePreset.push(widget.value);
          break; // 첫 번째 활성화된 프리셋만 저장
        }
      }
      return JSON.stringify(activePreset);
    }

    async function updateWidgets(node, subfolder, isInitializing = false) {
      const standardWidgets = node.widgets.filter(w => w.type !== "custom");
      const outputWidget = standardWidgets.find(w => w.name === "output_loras");
      const bypassWidget = standardWidgets.find(w => w.name === "bypass");
      const subfolderWidget = standardWidgets.find(w => w.name === "subfolder");

      if (!outputWidget) {
        console.error("[PresetSelectorV2] Output widget not found!");
        return;
      }

      let currentSubfolder = subfolder;
      if (isInitializing && node) {
        const savedSubfolder = node.widgets_values[
          node.widgets.findIndex(w => w.name === "subfolder")
        ];
        if (savedSubfolder) {
          currentSubfolder = savedSubfolder;
          if (subfolderWidget) {
            subfolderWidget.value = currentSubfolder;
          }
        }
      }

      const all = await getPresets();
      const filtered = filterPresets(all, currentSubfolder);
      const presetCount = Math.min(filtered.length, 20);
      const presetNames = ["none", ...filtered.map(p => p.display_name)];

      let activeDisplayNames = [];
      try {
        activeDisplayNames = JSON.parse(outputWidget.value || "[]");
      } catch (e) {
        console.error("Failed to parse output_loras:", e);
      }

      node.widgets = [...standardWidgets];

      // 커스텀 위젯들에 대한 단일 선택 로직 추가
      for (let i = 0; i < presetCount; i++) {
        const preset = filtered[i];
        if (!preset || preset.path === "none") continue;

        const displayName = preset.display_name || "none";

        const customW = createComboToggleWidget({
          name: `preset-combo-${i + 1}`,
          values: presetNames,
          defaultValue: displayName,
          onChange: (value) => {
            if (bypassWidget?.value) return;
            outputWidget.value = calculateActivePreset(node);
            app.graph.setDirtyCanvas(true);
          },
          onToggle: (isActive) => {
            if (bypassWidget?.value) return;

            // 이 위젯이 활성화되면 다른 모든 위젯은 비활성화
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

        // 이전 상태 복원 - 단일 선택만 허용
        if (activeDisplayNames.includes(displayName)) {
          customW.isActive = true;
          // 이미 활성화된 위젯이 있으면 이전 것들은 모두 비활성화
          node.widgets.forEach(widget => {
            if (widget.type === "custom") {
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
    }

    const origGetExtraMenuOptions = nodeType.prototype.getExtraMenuOptions;
    nodeType.prototype.getExtraMenuOptions = function(_, options) {
      if (origGetExtraMenuOptions) {
        origGetExtraMenuOptions.apply(this, arguments);
      }

      options.unshift({
        content: "Clear Preset",
        callback: () => {
          this.widgets.forEach(widget => {
            if (widget.type === "custom") {
              widget.value = "none";
              widget.isActive = false;
            }
          });

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
          console.error("[PresetSelectorV2] Required widgets not found!");
          return;
        }

        subfolderWidget.callback = async () => {
          const subfolder = subfolderWidget.value;
          this.title = `Group: ${subfolder}`;
          await updateWidgets(this, subfolder, false);
        };

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

        bypassWidget.callback = () => {
          this.widgets.forEach(widget => {
            if (widget.type === "custom") {
              widget.disabled = bypassWidget.value;
            }
          });
          app.graph.setDirtyCanvas(true);
        };

        const waitForNode = () => {
          if (!this || !this.widgets_values) {
            setTimeout(waitForNode, 500);
            return;
          }
          updateWidgets(this, subfolderWidget.value, true);
          app.graph.setDirtyCanvas(true);
        };

        waitForNode();
      } catch (error) {
        console.error("[PresetSelectorV2] Error in onNodeCreated:", error);
      }
    };

    const origSerialize = nodeType.prototype.serialize;
    nodeType.prototype.serialize = function() {
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

    const origConfigure = nodeType.prototype.configure;
    nodeType.prototype.configure = function(info) {
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