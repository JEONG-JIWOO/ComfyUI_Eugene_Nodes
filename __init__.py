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
    DictJSONLoad,
    XMLTagExtractor,
    JSONFileSelector,
    DictSaveToFolder,
    DictLoadFromPath,
)

from .nodes.dictionary_bus import (
    DictBus,
    DictBusUnpack,
    DictBusEdit,
    DictBusUpdateFirstDict
)

from .nodes.lora_nodes import (
    PresetEditor,
    PresetSelectorV2,
    AdvancedLoraLoader,
    ListBasedLoraLoader,
    ListBasedLoraLoadOnly,
    DictBasedLoraLoader,
    MultiPromptGenerator,
    setup_web,
    PresetSelectorV2Multi,
)

from .nodes.latent_node import (
    LatentExpander,
    SetMultipleLatentNoiseMasks,
    SetMultipleImageNoiseMasks,
    CropMultipleImagesByMasks,
    MergeInpaintedLatent,
)

from .nodes.mask_nodes import (
    MaskSplitAndGrow2Ways,
    MaskSplitAndGrow3Ways,
)
from .nodes.dwpose_mask import (
    DwposeMask,
    YoloPoseMask,
)

from .nodes.keypoint_extractor import (
    KeypointExtractor,
    KeypointDivider,
    YoloPoseKeypointDivider,
)

from .nodes.mask_mover import (
    MaskMover,
)

NODE_CLASS_MAPPINGS = {
    # Dictionary Nodes
    "DictUpdate1": DictUpdate1,
    "DictUpdate5": DictUpdate5,
    "DictUpdate10": DictUpdate10,
    "DictTemplate": DictTemplate,
    "DictMultilineSelect": DictMultilineSelect,
    "DictJSONSave":DictJSONSave,
    "DictJSONLoad": DictJSONLoad,
    "XMLTagExtractor": XMLTagExtractor,
    "DictBusUpdateFirstDict": DictBusUpdateFirstDict,
    "JSONFileSelector": JSONFileSelector,
    "DictSaveToFolder": DictSaveToFolder,
    "DictLoadFromPath": DictLoadFromPath,

    # Dictionary Bus Nodes
    "DictBus": DictBus,
    "DictBusUnpack": DictBusUnpack,
    "DictBusEdit": DictBusEdit,

    # LoRA Nodes
    "PresetEditor" : PresetEditor,
    "LoraPresetSelectorV2": PresetSelectorV2,
    "LoraPresetLoader": AdvancedLoraLoader,
    "LoraPresetListLoader": ListBasedLoraLoader,
    "ListBasedLoraLoadOnly": ListBasedLoraLoadOnly,
    "DictBasedLoraLoader":DictBasedLoraLoader,
    "MultiPromptGenerator":MultiPromptGenerator,
    "PresetSelectorV2Multi":PresetSelectorV2Multi,

    # Latent Nodes
    "LatentExpander" : LatentExpander,
    "SetMultipleLatentNoiseMasks": SetMultipleLatentNoiseMasks,
    "SetMultipleImageNoiseMasks": SetMultipleImageNoiseMasks,
    "CropMultipleImagesByMasks": CropMultipleImagesByMasks,
    "MergeInpaintedLatent": MergeInpaintedLatent,

    # Mask Nodes
    "MaskSplitAndGrow2Ways": MaskSplitAndGrow2Ways,
    "MaskSplitAndGrow3Ways": MaskSplitAndGrow3Ways,
    "DwposeMask": DwposeMask,
    "YoloPoseMask": YoloPoseMask,

    # Keypoint Extractor Node
    "KeypointExtractor": KeypointExtractor,
    "KeypointDivider": KeypointDivider,
    "YoloPoseKeypointDivider": YoloPoseKeypointDivider,

    "MaskMover": MaskMover,
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
    "XMLTagExtractor": "XML Tag Content Extractor",
    "JSONFileSelector": "JSON File Selector",
    "DictBusUpdateFirstDict": "Dictionary Bus Update First Dict",
    "DictSaveToFolder": "Dictionary Save To Custom Folder",
    "DictLoadFromPath": "Dictionary Load From File Path",

    # Dictionary Bus Nodes
    "DictBus": "Dictionary Bus",
    "DictBusUnpack": "Dictionary Bus Unpack",
    "DictBusEdit": "Dictionary Bus Edit",

    # LoRA Nodes
    "PresetEditor" : "Preset Editor",
    "LoraPresetSelectorV2" : "LoRA Preset Selector V2, DICT",
    "LoraPresetLoader": "LoRA Preset Loader & Encoder",
    "LoraPresetListLoader": "LoRA Preset List Loader & Encoder",
    "ListBasedLoraLoadOnly" : "LoRA Preset List Loader Only",
    "DictBasedLoraLoader": "LoRA Preset Dict Loader",
    "MultiPromptGenerator": "Multi Prompt Generator",
    "PresetSelectorV2Multi": "Multi LoRA Preset Selector",
    
    # Latent Nodes
    "LatentExpander": "Latent Expander",
    "SetMultipleLatentNoiseMasks": "Set Multiple Latent Noise Masks",
    "SetMultipleImageNoiseMasks": "Set Multiple Image Noise Masks",
    "CropMultipleImagesByMasks": "Crop Multiple Images By Masks",
    "MergeInpaintedLatent": "Merge Inpainted Latent",

    # Mask Nodes
    "MaskSplitAndGrow2Ways": "Mask Split and Grow 2 Ways",
    "MaskSplitAndGrow3Ways": "Mask Split and Grow 3 Ways",
    "DwposeMask": "Dwpose Mask",
    "YoloPoseMask": "Yolo Pose Mask",

    # Keypoint Extractor Node
    "KeypointExtractor": "Keypoint Extractor",
    "KeypointDivider": "Keypoint Divider",
    "YoloPoseKeypointDivider": "Yolo Pose Keypoint Divider",
    "MaskMover": "Mask Mover",
}

# Get the web server instance from ComfyUI
try:
    import server

    setup_web(server.PromptServer.instance)
except ImportError:
    print("\033[33mWarning: ComfyUI server module not found, web services not initialized\033[0m")

WEB_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "js")
__version__ = "1.1.0"