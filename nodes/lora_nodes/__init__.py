"""
LoRA Nodes Package
Provides nodes for managing and applying LoRA presets in ComfyUI
"""

import os
from .preset_nodes import PresetSaver, PresetSelector
from .loader_nodes import AdvancedLoraLoader, ListBasedLoraLoader
from .web import setup_routes

__all__ = [
    'PresetSaver',
    'PresetSelector',
    'AdvancedLoraLoader',
    'ListBasedLoraLoader'
]

# Web directory for JavaScript files
WEB_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "js")

def setup_js():
    """Ensure JavaScript files are in the correct location"""
    # Add any JS setup code here if needed
    pass

def setup_web(server):
    """Setup web routes and services"""
    setup_routes(server)
    setup_js()
    print("\033[34mEugene's LoRA Nodes: \033[92mLoaded\033[0m")