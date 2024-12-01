"""
Eugene's ComfyUI Custom Utility Nodes
A collection of dictionary-based utility nodes for ComfyUI workflows
"""

from .nodes.dictionary_nodes import (
    DictUpdate1,
    DictUpdate5,
    DictUpdate10,
    DictTemplate,
    DictMultilineSelect
)

NODE_CLASS_MAPPINGS = {
    "DictUpdate1": DictUpdate1,
    "DictUpdate5": DictUpdate5,
    "DictUpdate10": DictUpdate10,
    "DictTemplate": DictTemplate,
    "DictMultilineSelect": DictMultilineSelect,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DictUpdate1": "Dictionary Update (1 pair)",
    "DictUpdate5": "Dictionary Update (5 pairs)",
    "DictUpdate10": "Dictionary Update (10 pairs)",
    "DictTemplate": "Dictionary Template",
    "DictMultilineSelect": "Dictionary Multiline Select",
}

__version__ = "1.0.0"