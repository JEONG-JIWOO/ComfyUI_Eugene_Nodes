"""
LoRA Preset Helper Module
Provides utility functions for managing LoRA presets in ComfyUI
"""

import json
import os
import re
import folder_paths
import comfy.utils
import comfy.sd
import torch


class LoraPresetHelper:
    @staticmethod
    def get_lora_folder_path():
        """Returns the path to the LoRA folder."""
        return folder_paths.get_folder_paths("loras")[0]

    @classmethod
    def list_presets(cls):
        """
        Lists all available LoRA preset files.
        Returns a list of tuples (file_path, display_name).
        Display name uses nickname if available, otherwise uses file path.
        """
        lora_dir = cls.get_lora_folder_path()
        preset_files = [("none", "none")]
        preset_data = cls.load_preset_data()

        for root, _, files in os.walk(lora_dir):
            for file in files:
                if file.endswith('_preset.json'):
                    rel_path = os.path.relpath(os.path.join(root, file), lora_dir)
                    display_name = preset_data.get(rel_path, {}).get("nickname", rel_path)
                    preset_files.append((rel_path, display_name))

        return sorted(preset_files, key=lambda x: x[1].lower())

    @classmethod
    def load_preset_data(cls):
        """Loads all LoRA preset data."""
        lora_dir = cls.get_lora_folder_path()
        preset_data = {}

        for root, _, files in os.walk(lora_dir):
            for file in files:
                if file.endswith('_preset.json'):
                    rel_path = os.path.relpath(os.path.join(root, file), lora_dir)
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            preset_data[rel_path] = json.load(f)
                    except json.JSONDecodeError:
                        print(f"Error decoding JSON from {rel_path}")

        return preset_data

    @classmethod
    def get_subfolder_list(cls):
        """
        Returns a list of all subfolders in the LoRA directory.
        Includes the root folder.
        """
        lora_dir = cls.get_lora_folder_path()
        subfolders = {"root"}

        for root, dirs, _ in os.walk(lora_dir):
            for dir_name in dirs:
                rel_path = os.path.relpath(os.path.join(root, dir_name), lora_dir)
                subfolders.add(rel_path)

        return sorted(list(subfolders))

    @classmethod
    def get_preset_list(cls, subfolder):
        """
        Returns a list of presets in the specified subfolder.
        Returns root folder presets if subfolder is 'root'.
        """
        all_presets = cls.list_presets()

        if subfolder == "root":
            return [preset[1] for preset in all_presets
                    if preset[0] == "none" or "/" not in preset[0].replace("\\", "/")]
        else:
            subfolder_path = subfolder.replace("\\", "/")
            return [preset[1] for preset in all_presets
                    if preset[0] == "none" or
                    preset[0].replace("\\", "/").startswith(subfolder_path + "/")]

    @staticmethod
    def save_preset(preset_name, lora_data, suffix="", nickname=None):
        """Saves a LoRA preset."""
        lora_dir = LoraPresetHelper.get_lora_folder_path()
        file_name = f"{preset_name}{suffix}_preset.json"
        file_path = os.path.join(lora_dir, file_name)

        if nickname:
            lora_data["nickname"] = nickname

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(lora_data, f, ensure_ascii=False, indent=4)

        return file_path

    @staticmethod
    def clean_prompt(prompt):
        """
        Cleans the prompt by removing duplicate commas, unnecessary spaces, and newlines.
        """
        if not prompt or prompt.isspace():
            return ""

        cleaned = re.sub(r'\n+', ' ', prompt)
        cleaned = re.sub(r',', ' , ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'\s*,\s*,\s*', ', ', cleaned)
        cleaned = cleaned.strip(' ,')

        return cleaned

    @staticmethod
    def encode_prompt(clip, prompt):
        """Encodes a prompt using the CLIP model."""
        tokens = clip.tokenize(prompt)
        cond, pooled = clip.encode_from_tokens(tokens, return_pooled=True)
        return [[cond, {"pooled_output": pooled}]]

    @staticmethod
    def replace_dict_keys(text, input_dict):
        """Replaces dictionary keys in text with their values."""

        def replace_key(match):
            key = match.group(1)
            return str(input_dict.get(key, match.group(0)))

        return re.sub(r'\{([^}]+)\}', replace_key, text)

    @staticmethod
    def load_and_apply_lora(loaded_loras, model, clip, lora_path, strength, clip_strength):
        """Loads and applies a LoRA to the model and CLIP."""
        if lora_path not in loaded_loras:
            lora = comfy.utils.load_torch_file(lora_path, safe_load=True)
            loaded_loras[lora_path] = lora
        else:
            lora = loaded_loras[lora_path]

        return comfy.sd.load_lora_for_models(model, clip, lora, strength, clip_strength)