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
                rel_path = os.path.relpath(os.path.join(root, file), lora_dir)
                if file.endswith('.json'):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            preset_data[rel_path] = json.load(f)
                    except json.JSONDecodeError:
                        print(f"Error decoding JSON from {rel_path}")
                    except :
                        pass
        return preset_data

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
        """Replaces dictionary keys in text with their values.
           만약 해당 키가 없으면 빈 문자열("")로 대체합니다.
        """

        def replace_key(match):
            key = match.group(1)
            return str(input_dict.get(key, ""))  # 키가 없으면 빈 문자열 반환

        return re.sub(r'\{([^}]+)\}', replace_key, text)

    @staticmethod
    def load_and_apply_lora(loaded_loras, model, clip, lora_path, strength, clip_strength):
        """Loads and applies a LoRA to the model and CLIP.

        In case of any exception, the original (model, clip) is returned.
        """
        try:
            # safetensor 로라가 상대경로여서 못 찾는 경우 절대경로로 재시도
            if not os.path.exists(lora_path):
                LORA_BASE_PATH = folder_paths.get_folder_paths("loras")[0]
                candidate_path = os.path.join(LORA_BASE_PATH, lora_path)
                if os.path.exists(candidate_path):
                    lora_path = candidate_path
                else:
                    print(f"LoRA file not found: {lora_path}, ignore")
                    return (model, clip)

            if lora_path not in loaded_loras:
                lora = comfy.utils.load_torch_file(lora_path, safe_load=True)
                loaded_loras[lora_path] = lora
            else:
                lora = loaded_loras[lora_path]

            return comfy.sd.load_lora_for_models(model, clip, lora, strength, clip_strength)
        except Exception as e:
            print(f"Exception occurred in load_and_apply_lora: {str(e)}")
            return (model, clip)
