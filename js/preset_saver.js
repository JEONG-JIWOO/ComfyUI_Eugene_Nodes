import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "LoraPresetSaver.extension",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeType.comfyClass !== "LoraPresetSaver") return;

        const origOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = async function () {
            if (origOnNodeCreated) {
                origOnNodeCreated.apply(this, arguments);
            }

            const subfolderWidget = this.widgets.find(w => w.name === "subfolder");
            const loraNameWidget = this.widgets.find(w => w.name === "lora_name");

            if (subfolderWidget && loraNameWidget) {
                subfolderWidget.callback = async () => {
                        try {
                            const subfolder = subfolderWidget.value;
                            const response = await api.fetchApi("/folder_paths");
                            const data = await response.json();
                            const loras = data.loras || [];

                            const filtered = loras.filter(file => {
                                const path = file.replace(/\\/g, "/");
                                return subfolder === "root" ?
                                       !path.includes("/") :
                                       path.startsWith(subfolder + "/");
                            });

                            loraNameWidget.options.values = ["none", ...filtered];
                            app.graph.setDirtyCanvas(true);
                        } catch (error) {
                            console.error("[PresetSaver] Error:", error);
                        }
                    };
            }
        };
    }
});