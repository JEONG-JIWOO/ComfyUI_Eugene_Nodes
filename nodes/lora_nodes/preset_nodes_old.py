"""
LoRA Preset Management Nodes
Provides nodes for saving and selecting LoRA presets
"""

import folder_paths
import os
import json
from .helper import LoraPresetHelper

class PresetSaver:
    @classmethod
    def INPUT_TYPES(cls):
        lora_files = folder_paths.get_filename_list("loras")
        return {
            "required": {
                "triggered": ("BOOLEAN", {"default": False}),
                "suffix": ("STRING", {"default": ""}),
            },
            "optional": {
                **{f"lora_{i + 1}_{param}":
                       (["none"] + lora_files,) if param == "name" else
                       ("FLOAT", {"default": 1.0, "min": -100.0, "max": 100.0, "step": 0.01}) if param in ["strength", "clip_strength"] else
                       ("STRING", {"multiline": True, "default": ""}) if param in ["prompt_positive", "prompt_negative"] else
                       ("STRING", {"default": ""})
                   for i in range(5) for param in ["name", "nickname", "strength", "clip_strength", "prompt_positive", "prompt_negative"]}
            }
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "save_preset"
    CATEGORY = "lora/preset"

    @classmethod
    def save_preset(cls, triggered, suffix, **kwargs):
        """Saves multiple LoRA presets at once."""
        if not triggered:
            return ("LoRA presets not saved. Set 'triggered' to True to save.",)

        saved_files = []
        for i in range(5):
            lora_name = kwargs.get(f"lora_{i + 1}_name")
            if lora_name and lora_name != "none":
                preset_name = os.path.splitext(lora_name)[0]
                nickname = kwargs.get(f"lora_{i + 1}_nickname", "")
                lora_data = {
                    "lora_name": lora_name,
                    "lora_path": os.path.join(LoraPresetHelper.get_lora_folder_path(), lora_name),
                    "strength": kwargs.get(f"lora_{i + 1}_strength", 1.0),
                    "clip_strength": kwargs.get(f"lora_{i + 1}_clip_strength", 1.0),
                    "prompt_positive": kwargs.get(f"lora_{i + 1}_prompt_positive", ""),
                    "prompt_negative": kwargs.get(f"lora_{i + 1}_prompt_negative", ""),
                }
                saved_file = LoraPresetHelper.save_preset(preset_name, lora_data, suffix, nickname)
                saved_files.append(saved_file)

        return (f"LoRA presets saved to: {', '.join(saved_files)}",)


class PresetSelector:
    # Class variables for storing preset data
    all_subfolders = []
    all_presets = []

    @classmethod
    def initialize_data(cls):
        """Initialize all data when node is loaded"""
        cls.all_subfolders = LoraPresetHelper.get_subfolder_list()
        cls.all_presets = LoraPresetHelper.list_presets()

    @classmethod
    def update_data(cls):
        """Update data method"""
        cls.all_subfolders = LoraPresetHelper.get_subfolder_list()
        cls.all_presets = LoraPresetHelper.list_presets()
        return {
            "subfolders": cls.all_subfolders,
            "presets": [
                {"path": path, "display_name": display_name}
                for path, display_name in cls.all_presets
            ]
        }

    @classmethod
    def INPUT_TYPES(cls):
        if not cls.all_subfolders:
            cls.initialize_data()

        return {
            "required": {
                "subfolder": (cls.all_subfolders,),
                "preset": ([preset[1] for preset in cls.all_presets],),
                "weight": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                "bypass": ("BOOLEAN", {"default": False}),
                "refresh": ("BOOLEAN", {"default": False})
            },
            "optional": {
                "lora_list": ("LIST",),
            }
        }

    RETURN_TYPES = ("LIST",)
    RETURN_NAMES = ("lora_list",)
    FUNCTION = "select_preset"
    CATEGORY = "lora/preset"

    def select_preset(self, subfolder, preset, weight, bypass, refresh, lora_list=None):
        """Process preset selection"""
        if refresh:
            self.update_data()

        current_list = list(lora_list) if lora_list is not None else []

        try:
            if bypass or preset == "none":
                return (current_list,)

            preset_path = None
            for path, display_name in self.all_presets:
                if display_name == preset:
                    preset_path = path
                    break

            if preset_path is None:
                print(f"Warning: No matching preset found for display_name: {preset}")
                return (current_list,)

            if preset_path not in current_list:
                current_list.append(preset_path)

            return (current_list,)

        except Exception as e:
            print(f"Error in select_preset: {e}")
            return (current_list,)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        cls.all_subfolders = LoraPresetHelper.get_subfolder_list()
        cls.all_presets = LoraPresetHelper.list_presets()
        return True



class MultiPresetSelector:
    all_subfolders = []
    all_presets = []

    @classmethod
    def INPUT_TYPES(cls):
        if not cls.all_subfolders:
            cls.initialize_data()

        return {
            "required": {
                "subfolder": (cls.all_subfolders,),
                "weight": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                "bypass": ("BOOLEAN", {"default": False}),
                "refresh": ("BOOLEAN", {"default": False}),
                "output_loras": ("STRING", {"default": "[]"}),  # display_name list as JSON string
            },
            "optional": {
                "input_lora_list": ("LIST",)  # 다른 노드에서 입력받을 프리셋 경로 리스트
            }
        }

    RETURN_TYPES = ("LIST",)
    RETURN_NAMES = ("lora_list",)
    FUNCTION = "select_presets"
    CATEGORY = "lora/preset"

    @classmethod
    def initialize_data(cls):
        cls.all_subfolders = LoraPresetHelper.get_subfolder_list()
        cls.all_presets = LoraPresetHelper.list_presets()

    @classmethod
    def update_data(cls):
        cls.initialize_data()
        return {
            "subfolders": cls.all_subfolders,
            "presets": [
                {"path": path, "display_name": display_name}
                for path, display_name in cls.all_presets
            ]
        }

    def select_presets(self, subfolder, bypass,  weight, refresh, output_loras, input_lora_list=None):
        if refresh:
            self.update_data()

        if bypass:
            return (input_lora_list if input_lora_list is not None else [],)

        try:
            # JSON 문자열을 Python 리스트로 변환 (display_name 리스트)
            display_names = json.loads(output_loras)

            # display_name을 preset_path로 변환
            preset_paths = list(input_lora_list) if input_lora_list is not None else []
            for display_name in display_names:
                # all_presets에서 해당하는 path 찾기
                for path, name in self.all_presets:
                    if name == display_name:
                        preset_paths.append(path)
                        break
            return (preset_paths,)

        except json.JSONDecodeError:
            print(f"Error decoding output_loras JSON: {output_loras}")
            return ([],)
        except Exception as e:
            print(f"Error processing presets: {str(e)}")
            return ([],)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        cls.initialize_data()
        return True


