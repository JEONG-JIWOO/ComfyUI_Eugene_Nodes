import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "LoraPresetSelector.extension",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        console.log("LoraPresetSelector extension Loaded");
        if (nodeType.comfyClass !== "LoraPresetSelector") {
            return;
        }

        let cachedPresets = null;

        async function refreshPresets() {
            try {
                const response = await api.fetchApi('/lora_presets/refresh', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                cachedPresets = data.presets || [];
                return data;
            } catch (error) {
                console.error("Failed to refresh presets:", error);
                return null;
            }
        }

        async function getPresets() {
            if (cachedPresets) {
                return cachedPresets;
            }

            try {
                const response = await api.fetchApi('/lora_presets', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });

                const data = await response.json();
                console.log("Parsed API response:", data);

                cachedPresets = data.presets || [];
                return cachedPresets;
            } catch (error) {
                console.error("Failed to fetch presets:", error);
                return [];
            }
        }

        function filterPresets(presets, subfolder) {
            console.log("Filtering for subfolder:", subfolder);
            return presets.filter(preset => {
                if (preset.path === "none") return true;

                const normalizedPath = preset.path.replace(/\\/g, "/");
                console.log("Checking path:", normalizedPath);

                const normalizedSubfolder = subfolder.replace(/\\/g, "/");

                if (normalizedSubfolder === "root") {
                    const pathParts = normalizedPath.split("/");
                    const isRootLevel = pathParts.length <= 2;
                    console.log(`Root check for ${normalizedPath}: ${isRootLevel}`);
                    return isRootLevel;
                } else {
                    const isInSubfolder = normalizedPath.includes(normalizedSubfolder);
                    console.log(`Subfolder check for ${normalizedPath} with ${normalizedSubfolder}: ${isInSubfolder}`);
                    return isInSubfolder;
                }
            });
        }

        const origOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = async function() {
            if (origOnNodeCreated) {
                origOnNodeCreated.apply(this);
            }

            const subfolderWidget = this.widgets.find(w => w.name === "subfolder");
            const presetWidget = this.widgets.find(w => w.name === "preset");
            const refreshWidget = this.widgets.find(w => w.name === "refresh");

            if (!subfolderWidget || !presetWidget) {
                console.warn("Required widgets not found");
                return;
            }

            if (refreshWidget) {
                refreshWidget.callback = async () => {
                    if (refreshWidget.value) {
                        console.log("Refreshing presets...");
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

            subfolderWidget.callback = async () => {
                const subfolder = subfolderWidget.value;
                console.log("Subfolder changed to:", subfolder);

                const allPresets = await getPresets();
                console.log("All presets:", allPresets);

                const filteredPresets = filterPresets(allPresets, subfolder);
                console.log("Filtered presets:", filteredPresets);

                const presetNames = filteredPresets.map(p => p.display_name);
                if (!presetNames.includes("none")) {
                    presetNames.unshift("none");
                }

                console.log("Setting preset options:", presetNames);

                presetWidget.options.values = presetNames;
                presetWidget.value = presetNames[0] || "none";

                app.graph.setDirtyCanvas(true);
            };

            await subfolderWidget.callback();
        };
    }
});