"""
Eugene's ComfyUI Custom Utility Nodes
A collection of dictionary-based utility nodes for ComfyUI workflows
"""

import os
from .nodes.dictionary_nodes import (
    DictUpdate1,
    DictUpdate5,
    DictUpdate10,
    DictTemplate,
    DictMultilineSelect,
    DictJSONSave,
    DictJSONLoad
)

from .nodes.dictionary_bus import (
    DictBus,
    DictBusUnpack,
    DictBusEdit
)

from .nodes.lora_nodes import (
    PresetSaver,
    PresetSelector,
    AdvancedLoraLoader,
    ListBasedLoraLoader,
    setup_web
)

from .nodes.remote_executor import *

NODE_CLASS_MAPPINGS = {
    # Dictionary Nodes
    "DictUpdate1": DictUpdate1,
    "DictUpdate5": DictUpdate5,
    "DictUpdate10": DictUpdate10,
    "DictTemplate": DictTemplate,
    "DictMultilineSelect": DictMultilineSelect,
    "DictJSONSave":DictJSONSave,
    "DictJSONLoad": DictJSONLoad,
    # Dictionary Bus Nodes
    "DictBus": DictBus,
    "DictBusUnpack": DictBusUnpack,
    "DictBusEdit": DictBusEdit,

    # LoRA Nodes
    "LoraPresetSaver": PresetSaver,
    "LoraPresetSelector": PresetSelector,
    "LoraPresetLoader": AdvancedLoraLoader,
    "LoraPresetListLoader": ListBasedLoraLoader,

    "RemoteWorkflowExecutor": RemoteWorkflowExecutor,
    "DatabaseStorage": DatabaseNode,
    "GateServer": GateServerNode,
    "GateClient": GateClientNode

}

NODE_DISPLAY_NAME_MAPPINGS = {
    # Dictionary Nodes
    "DictUpdate1": "Dictionary Update (1 pair)",
    "DictUpdate5": "Dictionary Update (5 pairs)",
    "DictUpdate10": "Dictionary Update (10 pairs)",
    "DictTemplate": "Dictionary Template",
    "DictMultilineSelect": "Dictionary Multiline Select",
    "DictJSONSave": "Dictionary Save as Json",
    "DictJSONLoad": "Dictionary Load from Json",

    # Dictionary Bus Nodes
    "DictBus": "Dictionary Bus",
    "DictBusUnpack": "Dictionary Bus Unpack",
    "DictBusEdit": "Dictionary Bus Edit",

    # LoRA Nodes
    "LoraPresetSaver": "LoRA Preset Saver",
    "LoraPresetSelector": "LoRA Preset Selector",
    "LoraPresetLoader": "LoRA Preset Loader & Encoder",
    "LoraPresetListLoader": "LoRA Preset List Loader & Encoder",

    "RemoteWorkflowExecutor": "Remote Workflow Executor",
    "DatabaseStorage": "Database Storage",
    "GateServer": "Gate Server",
    "GateClient": "Gate Client"
}

# Get the web server instance from ComfyUI
try:
    import server

    setup_web(server.PromptServer.instance)
except ImportError:
    print("\033[33mWarning: ComfyUI server module not found, web services not initialized\033[0m")

WEB_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "js")
__version__ = "1.1.0"