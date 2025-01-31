"""
LoRA Loader Nodes
Provides nodes for loading and applying LoRA presets to models
"""
import os
import re
import json
from .helper import LoraPresetHelper


class AdvancedLoraLoader:
    def __init__(self):
        self.loaded_loras = {}

    @classmethod
    def INPUT_TYPES(cls):
        presets = LoraPresetHelper.list_presets()
        preset_dict = {display_name: file_path for file_path, display_name in presets}

        return {
            "required": {
                "positive_prefix": ("STRING", {"multiline": True}),
                "positive_suffix": ("STRING", {"multiline": True}),
                "negative_prefix": ("STRING", {"multiline": True}),
                "negative_suffix": ("STRING", {"multiline": True}),
                "stop_at_clip_layer": ("INT", {"default": -1, "min": -24, "max": 1, "step": 1}),
            },
            "optional": {
                "input_dictionary": ("DICT",),
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "vae": ("VAE",),
                "basic_pipe": ("BASIC_PIPE",),
                "dict_bus": ("DICT_BUS",),
                **{f"lora_{i + 1}_{param}":
                       (list(preset_dict.keys()),) if param == "preset" else
                       (
                       "FLOAT", {"default": 1.0, "min": -100.0, "max": 100.0, "step": 0.01}) if param == "strength" else
                       ("STRING", {"multiline": True, "default": ""})
                   for i in range(5) for param in ["preset", "strength"]}
            }
        }

    RETURN_TYPES = ("DICT", "MODEL", "CLIP", "VAE", "CONDITIONING", "CONDITIONING", "BASIC_PIPE", "STRING", "STRING")
    RETURN_NAMES = ("input_dict", "model", "clip", "vae", "positive_conditioning", "negative_conditioning",
                    "basic_pipe", "positive_prompt", "negative_prompt")
    FUNCTION = "process"
    CATEGORY = "lora/loader"

    def process(self, positive_prefix, positive_suffix, negative_prefix, negative_suffix,
                stop_at_clip_layer, input_dictionary={}, model=None, clip=None, vae=None,
                basic_pipe=None, dict_bus=None, **kwargs):

        # Create preset display name to file path mapping
        presets = LoraPresetHelper.list_presets()
        preset_dict = {display_name: file_path for file_path, display_name in presets}

        # Handle input priority from different sources
        if dict_bus is not None:
            dict_mb, model_mb, clip_mb, vae_mb, _, _, _ = dict_bus
            input_dictionary = input_dictionary or dict_mb
            model = model or model_mb
            clip = clip or clip_mb
            vae = vae or vae_mb

        if basic_pipe is not None:
            model_bp, clip_bp, vae_bp, _, _ = basic_pipe
            model = model or model_bp
            clip = clip or clip_bp
            vae = vae or vae_bp

        assert model is not None and clip is not None and vae is not None, "Model, CLIP, and VAE are required"

        # Modify CLIP model
        if stop_at_clip_layer < 0:
            clip_modified = clip.clone()
            clip_modified.clip_layer(stop_at_clip_layer)
        else :
            clip_modified = clip

        # Process LoRA presets
        preset_data = LoraPresetHelper.load_preset_data()
        positive_prompts = [LoraPresetHelper.replace_dict_keys(positive_prefix, input_dictionary)]
        negative_prompts = [LoraPresetHelper.replace_dict_keys(negative_prefix, input_dictionary)]

        # Apply each LoRA preset
        for i in range(5):
            preset_display_name = kwargs.get(f"lora_{i + 1}_preset")
            if preset_display_name and preset_display_name != "none":
                preset_file = preset_dict[preset_display_name]
                preset_data_item = preset_data.get(preset_file)
                if preset_data_item is None:
                    raise ValueError(f"Preset data for {preset_file} not found.")

                lora_name = preset_data_item.get("lora_name")
                lora_path = preset_data_item.get("lora_path")
                if not os.path.isabs(lora_path):
                    lora_path = os.path.join(
                        os.path.dirname(os.path.join(LoraPresetHelper.get_lora_folder_path(), preset_file)),
                        lora_name
                    )

                strength = kwargs.get(f"lora_{i + 1}_strength", preset_data_item.get("strength", 1.0))
                clip_strength = strength  # Using same strength for clip

                positive_prompts.append(preset_data_item.get("prompt_positive", ""))
                negative_prompts.append(preset_data_item.get("prompt_negative", ""))

                model, clip_modified = LoraPresetHelper.load_and_apply_lora(
                    self.loaded_loras,
                    model,
                    clip_modified,
                    lora_path,
                    strength,
                    clip_strength
                )

        # Finalize prompts
        positive_prompts.append(LoraPresetHelper.replace_dict_keys(positive_suffix, input_dictionary))
        negative_prompts.append(LoraPresetHelper.replace_dict_keys(negative_suffix, input_dictionary))

        positive_prompt = LoraPresetHelper.clean_prompt(", ".join(positive_prompts))
        negative_prompt = LoraPresetHelper.clean_prompt(", ".join(negative_prompts))

        # Generate conditioning
        positive_conditioning = LoraPresetHelper.encode_prompt(clip_modified, positive_prompt)
        negative_conditioning = LoraPresetHelper.encode_prompt(clip_modified, negative_prompt)

        return (input_dictionary, model, clip_modified, vae, positive_conditioning, negative_conditioning,
                (model, clip, vae, positive_conditioning, negative_conditioning),
                positive_prompt, negative_prompt)


class ListBasedLoraLoader(AdvancedLoraLoader):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "positive_prefix": ("STRING", {"multiline": True}),
                "positive_suffix": ("STRING", {"multiline": True}),
                "negative_prefix": ("STRING", {"multiline": True}),
                "negative_suffix": ("STRING", {"multiline": True}),
                "stop_at_clip_layer": ("INT", {"default": -1, "min": -24, "max": 2, "step": 1}),
            },
            "optional": {
                "input_dictionary": ("DICT",),
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "vae": ("VAE",),
                "basic_pipe": ("BASIC_PIPE",),
                "dict_bus": ("DICT_BUS",),
                "preset_list": ("LIST",),
            }
        }

    FUNCTION = "process_list"
    CATEGORY = "lora/loader"

    def process_list(self, positive_prefix, positive_suffix, negative_prefix, negative_suffix,
                     stop_at_clip_layer, input_dictionary={}, model=None, clip=None, vae=None,
                     basic_pipe=None, dict_bus=None, preset_list=None):
        """Process LoRA presets from a list"""

        # Handle input sources
        if dict_bus is not None:
            dict_mb, model_mb, clip_mb, vae_mb, _, _, list_mb = dict_bus
            input_dictionary = input_dictionary or dict_mb
            model = model or model_mb
            clip = clip or clip_mb
            vae = vae or vae_mb
            preset_list = preset_list or list_mb

        if basic_pipe is not None:
            model_bp, clip_bp, vae_bp, _, _ = basic_pipe
            model = model or model_bp
            clip = clip or clip_bp
            vae = vae or vae_bp

        assert model is not None and clip is not None and vae is not None, "Model, CLIP, and VAE are required"

        # Modify CLIP model
        if stop_at_clip_layer < 0:
            clip_modified = clip.clone()
            clip_modified.clip_layer(stop_at_clip_layer)
        else :
            clip_modified = clip

        # Process prompts and LoRAs
        preset_data = LoraPresetHelper.load_preset_data()
        positive_prompts = [LoraPresetHelper.replace_dict_keys(positive_prefix, input_dictionary)]
        negative_prompts = [LoraPresetHelper.replace_dict_keys(negative_prefix, input_dictionary)]

        if preset_list:
            for preset_file in preset_list:
                preset_data_item = preset_data.get(preset_file)
                if preset_data_item is None:
                    raise ValueError(f"Preset data for {preset_file} not found.")

                lora_name = preset_data_item.get("lora_name")
                lora_path = preset_data_item.get("lora_path")
                if not os.path.isabs(lora_path):
                    lora_path = os.path.join(
                        os.path.dirname(os.path.join(LoraPresetHelper.get_lora_folder_path(), preset_file)),
                        lora_name
                    )

                strength = preset_data_item.get("strength", 1.0)
                clip_strength = preset_data_item.get("clip_strength", 1.0)

                positive_prompts.append(preset_data_item.get("prompt_positive", ""))
                negative_prompts.append(preset_data_item.get("prompt_negative", ""))

                if stop_at_clip_layer < 1:
                    model, clip_modified = LoraPresetHelper.load_and_apply_lora(
                        self.loaded_loras,
                        model,
                        clip_modified,
                        lora_path,
                        strength,
                        clip_strength
                    )

        # Finalize prompts
        positive_prompts.append(LoraPresetHelper.replace_dict_keys(positive_suffix, input_dictionary))
        negative_prompts.append(LoraPresetHelper.replace_dict_keys(negative_suffix, input_dictionary))

        positive_prompt = LoraPresetHelper.clean_prompt(", ".join(positive_prompts))
        negative_prompt = LoraPresetHelper.clean_prompt(", ".join(negative_prompts))
        positive_conditioning = None
        negative_conditioning = None

        if stop_at_clip_layer == 1:
            return (input_dictionary, model, clip_modified, vae, positive_conditioning, negative_conditioning,
                    (model, clip, vae, positive_conditioning, negative_conditioning),
                    positive_prompt, negative_prompt)
        try:
        # Generate conditioning
            positive_conditioning = LoraPresetHelper.encode_prompt(clip_modified, positive_prompt)
            negative_conditioning = LoraPresetHelper.encode_prompt(clip_modified, negative_prompt)
        except:
            pass
        return (input_dictionary, model, clip_modified, vae, positive_conditioning, negative_conditioning,
                (model, clip, vae, positive_conditioning, negative_conditioning),
                positive_prompt, negative_prompt)

class ListBasedLoraLoadOnly(AdvancedLoraLoader):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "positive_prefix": ("STRING", {"multiline": True}),
                "positive_suffix": ("STRING", {"multiline": True}),
                "negative_prefix": ("STRING", {"multiline": True}),
                "negative_suffix": ("STRING", {"multiline": True}),
                "text_only":("BOOLEAN",{"default": False})
            },
            "optional": {
                "input_dictionary": ("DICT",),
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "vae": ("VAE",),
                "basic_pipe": ("BASIC_PIPE",),
                "dict_bus": ("DICT_BUS",),
                "preset_list": ("LIST",),
            }
        }

    FUNCTION = "process_list"
    CATEGORY = "lora/loader"

    RETURN_TYPES = ("DICT", "MODEL", "CLIP", "VAE", "STRING", "STRING")
    RETURN_NAMES = ("input_dict", "model", "clip", "vae", "positive_prompt", "negative_prompt")

    def process_list(self, positive_prefix, positive_suffix, negative_prefix, negative_suffix,text_only,
                     input_dictionary={}, model=None, clip=None, vae=None,
                     basic_pipe=None, dict_bus=None, preset_list=None):
        """Process LoRA presets from a list"""

        # Handle input sources
        if dict_bus is not None:
            dict_mb, model_mb, clip_mb, vae_mb, _, _, list_mb = dict_bus
            input_dictionary = input_dictionary or dict_mb
            model = model or model_mb
            clip = clip or clip_mb
            vae = vae or vae_mb
            preset_list = preset_list or list_mb

        if basic_pipe is not None:
            model_bp, clip_bp, vae_bp, _, _ = basic_pipe
            model = model or model_bp
            clip = clip or clip_bp
            vae = vae or vae_bp

        if not text_only:
            assert model is not None and clip is not None and vae is not None, "Model, CLIP, and VAE are required"

        # Process prompts and LoRAs
        preset_data = LoraPresetHelper.load_preset_data()
        positive_prompts = [LoraPresetHelper.replace_dict_keys(positive_prefix, input_dictionary)]
        negative_prompts = [LoraPresetHelper.replace_dict_keys(negative_prefix, input_dictionary)]

        if preset_list:
            for preset_file in preset_list:
                preset_data_item = preset_data.get(preset_file)
                if preset_data_item is None:
                    raise ValueError(f"Preset data for {preset_file} not found.")

                lora_name = preset_data_item.get("lora_name")
                lora_path = preset_data_item.get("lora_path")
                if not os.path.isabs(lora_path):
                    lora_path = os.path.join(
                        os.path.dirname(os.path.join(LoraPresetHelper.get_lora_folder_path(), preset_file)),
                        lora_name
                    )

                strength = preset_data_item.get("strength", 1.0)
                clip_strength = preset_data_item.get("clip_strength", 1.0)

                positive_prompts.append(preset_data_item.get("prompt_positive", ""))
                negative_prompts.append(preset_data_item.get("prompt_negative", ""))
                if not text_only:
                    model, clip = LoraPresetHelper.load_and_apply_lora(
                        self.loaded_loras,
                        model,
                        clip,
                        lora_path,
                        strength,
                        clip_strength
                    )

        # Finalize prompts
        positive_prompts.append(LoraPresetHelper.replace_dict_keys(positive_suffix, input_dictionary))
        negative_prompts.append(LoraPresetHelper.replace_dict_keys(negative_suffix, input_dictionary))
        positive_prompt = LoraPresetHelper.clean_prompt(", ".join(positive_prompts))
        negative_prompt = LoraPresetHelper.clean_prompt(", ".join(negative_prompts))

        if text_only:
            return input_dictionary, None, None, None, positive_prompt, negative_prompt

        return input_dictionary, model, clip, vae, positive_prompt, negative_prompt


class DictBasedLoraLoader:
    loaded_loras = {}  # Cache for loaded LoRAs

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "positive_prefix": ("STRING", {"multiline": True}),
                "positive_suffix": ("STRING", {"multiline": True}),
                "negative_prefix": ("STRING", {"multiline": True}),
                "negative_suffix": ("STRING", {"multiline": True}),
                "stop_at_clip_layer": ("INT", {"default": -1, "min": -24, "max": 0, "step": 1}),
            },
            "optional": {
                "input_dictionary": ("DICT",),
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "vae": ("VAE",),
                "basic_pipe": ("BASIC_PIPE",),
                "dict_bus": ("DICT_BUS",),
                "lora_dict": ("DICT",),
                "do_conditioning": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("DICT", "MODEL", "CLIP", "VAE", "CONDITIONING", "CONDITIONING", "BASIC_PIPE", "STRING", "STRING")
    RETURN_NAMES = ("input_dict", "model", "clip", "vae", "positive_conditioning", "negative_conditioning",
                    "basic_pipe", "positive_prompt", "negative_prompt")
    FUNCTION = "process_loras"
    CATEGORY = "lora/loader"

    def _replace_lora_keys(self, text, input_dictionary, lora_dict):
        """Replace both input dictionary keys and lora keys in the text.
        Returns tuple of (processed_text, set of found lora keys)"""
        if not text:
            return "", set()

        # First replace input dictionary keys
        text = LoraPresetHelper.replace_dict_keys(text, input_dictionary)

        # Find all LoRA keys in the text
        found_keys = set(re.findall(r'\{#([^}]+)\}', text))

        # Then replace lora keys with prompts
        def replace_lora_key(match):
            key = match.group(1)
            if key in lora_dict:
                return lora_dict[key].get("positive_prompt", "")
            return ""  # Key not found, return empty string

        processed_text = re.sub(r'\{#([^}]+)\}', replace_lora_key, text)

        return processed_text, found_keys

    def _process_text_and_get_keys(self, text, input_dictionary, lora_dict):
        """Process text and return both processed text and found LoRA keys"""
        if not text:
            return "", set()
        return self._replace_lora_keys(text, input_dictionary, lora_dict)

    def process_loras(self, positive_prefix, positive_suffix, negative_prefix, negative_suffix,
                      stop_at_clip_layer, input_dictionary={}, model=None, clip=None, vae=None,
                      basic_pipe=None, dict_bus=None, lora_dict=None, do_conditioning=True):
        """Process LoRA dictionary and apply to model"""

        # Handle input sources
        if dict_bus is not None:
            dict_mb, model_mb, clip_mb, vae_mb, _, _, _ = dict_bus
            input_dictionary = input_dictionary or dict_mb
            model = model or model_mb
            clip = clip or clip_mb
            vae = vae or vae_mb

        if basic_pipe is not None:
            model_bp, clip_bp, vae_bp, _, _ = basic_pipe
            model = model or model_bp
            clip = clip or clip_bp
            vae = vae or vae_bp

        assert model is not None and clip is not None and vae is not None, "Model, CLIP, and VAE are required"
        lora_dict = lora_dict or {}

        # Modify CLIP model if needed
        if stop_at_clip_layer < 0:
            clip_modified = clip.clone()
            clip_modified.clip_layer(stop_at_clip_layer)
        else:
            clip_modified = clip

        # Process prompts and collect used LoRA keys
        used_lora_keys = set()

        # Process prefix prompts
        pos_prefix_text, pos_prefix_keys = self._process_text_and_get_keys(positive_prefix, input_dictionary, lora_dict)
        neg_prefix_text, neg_prefix_keys = self._process_text_and_get_keys(negative_prefix, input_dictionary, lora_dict)
        used_lora_keys.update(pos_prefix_keys)
        used_lora_keys.update(neg_prefix_keys)

        positive_prompts = [pos_prefix_text]
        negative_prompts = [neg_prefix_text]

        print(f"[DEBUG] Used LoRA keys: {used_lora_keys}")

        if lora_dict and used_lora_keys:
            # Process only LoRAs that were referenced in prompts
            for lora_key, lora_info in lora_dict.items():
                if lora_key not in used_lora_keys:
                    print(f"[DEBUG] Skipping unused LoRA: {lora_key}")
                    continue

                print(f"\n[DEBUG] Processing LoRA: {lora_key}")
                print(f"[DEBUG] LoRA info: {lora_info}")

                try:
                    if not isinstance(lora_info, dict):
                        print(f"Warning: Invalid LoRA info for key {lora_key}")
                        continue

                    preset_path = lora_info.get("path")
                    if not preset_path or preset_path == "none":
                        continue

                    # First load the JSON preset file
                    json_path = os.path.join(LoraPresetHelper.get_lora_folder_path(), preset_path)
                    with open(json_path, 'r') as f:
                        preset_data = json.load(f)

                    # Get the actual LoRA path from the preset
                    lora_path = preset_data.get("lora_path") or preset_data.get("lora_name")
                    if not lora_path:
                        print(f"[DEBUG] No LoRA path found in preset: {json_path}")
                        continue

                    # Get weights from preset
                    model_weight = lora_info.get("strength", 1.0)
                    clip_weight = lora_info.get("clip_strength", 1.0)
                    print(f"[DEBUG] Loaded weights from lora_info - Model: {model_weight}, CLIP: {clip_weight}")

                    # Print path info
                    print(f"[DEBUG] JSON preset path: {json_path}")
                    print(f"[DEBUG] LoRA path from preset: {lora_path}")

                    # Load and apply LoRA
                    if stop_at_clip_layer < 1:
                        print("[DEBUG] Applying LoRA with weights...")

                        # Use either the full path or join with the LoRA folder path
                        if os.path.isabs(lora_path):
                            final_lora_path = lora_path
                        else:
                            final_lora_path = os.path.join(LoraPresetHelper.get_lora_folder_path(), lora_path)

                        print(f"[DEBUG] Final LoRA path: {final_lora_path}")

                        model, clip_modified = LoraPresetHelper.load_and_apply_lora(
                            self.loaded_loras,
                            model,
                            clip_modified,
                            final_lora_path,
                            model_weight,
                            clip_weight
                        )

                except Exception as e:
                    print(f"Error processing LoRA {lora_key}: {str(e)}")
                    continue

        # Process suffix prompts
        pos_suffix_text, pos_suffix_keys = self._process_text_and_get_keys(positive_suffix, input_dictionary, lora_dict)
        neg_suffix_text, neg_suffix_keys = self._process_text_and_get_keys(negative_suffix, input_dictionary, lora_dict)
        used_lora_keys.update(pos_suffix_keys)
        used_lora_keys.update(neg_suffix_keys)

        positive_prompts.append(pos_suffix_text)
        negative_prompts.append(neg_suffix_text)

        # Clean and join prompts
        positive_prompt = LoraPresetHelper.clean_prompt(", ".join(filter(None, positive_prompts)))
        negative_prompt = LoraPresetHelper.clean_prompt(", ".join(filter(None, negative_prompts)))

        # Initialize and generate conditioning
        positive_conditioning = None
        negative_conditioning = None

        if do_conditioning:
            try:
                positive_conditioning = LoraPresetHelper.encode_prompt(clip_modified, positive_prompt)
                negative_conditioning = LoraPresetHelper.encode_prompt(clip_modified, negative_prompt)
            except Exception as e:
                print(f"Error encoding prompts: {str(e)}")

        # Prepare basic pipe for return
        basic_pipe = (model, clip, vae, positive_conditioning, negative_conditioning)

        return (input_dictionary, model, clip_modified, vae, positive_conditioning, negative_conditioning,
                basic_pipe, positive_prompt, negative_prompt)