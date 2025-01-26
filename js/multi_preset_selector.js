import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

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
        if (!preset || preset.path === "none") return true;
        const normPath = preset.path.replace(/\\/g, "/");
        if (normalizedSub === "root") {
          return normPath.split("/").length <= 2;
        }
        return normPath.startsWith(normalizedSub + "/");
      });
    }

    const origOnNodeCreated = nodeType.prototype.onNodeCreated;

    nodeType.prototype.onNodeCreated = async function () {
      if (origOnNodeCreated) {
        origOnNodeCreated.apply(this, arguments);
      }

      const savedData = this.data ?? this.properties ?? nodeData ?? {};

      const subfolderWidget = this.widgets.find(w => w.name === "subfolder");
      const presetWidgets = Array.from({length: 10}, (_, i) =>
        this.widgets.find(w => w.name === `preset${i + 1}`)
      );
      const refreshWidget = this.widgets.find(w => w.name === "refresh");

      if (!subfolderWidget || presetWidgets.some(w => !w)) {
        console.warn("[LoraMultiPresetSelector] Required widgets not found!");
        return;
      }

      if (refreshWidget) {
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
      }

      // Subfolder callback to update the node title and preset lists
      const origSubfolderCallback = subfolderWidget.callback;
      subfolderWidget.callback = async () => {
        if (typeof origSubfolderCallback === "function") {
          origSubfolderCallback.call(subfolderWidget);
        }

        const subfolder = subfolderWidget.value;
        this.title = `Group: ${subfolder}`; // Update node title with subfolder name

        const all = await getPresets();
        const filtered = filterPresets(all, subfolder);
        const presetNames = filtered.map(p => p.display_name || "none");
        const finalList = Array.from(new Set(["none", ...presetNames]));

        presetWidgets.forEach(widget => {
          widget.options.values = finalList;
        });

        app.graph.setDirtyCanvas(true);
      };

      // Load saved data
      const savedSubfolder = savedData.properties?.subfolder;
      if (savedSubfolder !== undefined) {
        subfolderWidget.value = savedSubfolder;
        this.title = `Group: ${savedSubfolder}`;
      }

      presetWidgets.forEach((widget, index) => {
        const savedPreset = savedData.properties?.[`preset${index + 1}`];
        if (savedPreset !== undefined) {
          widget.value = savedPreset;
        }
      });

      await subfolderWidget.callback();
    };
  }
});