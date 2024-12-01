"""
LoRA Loader Nodes
Provides nodes for loading and applying LoRA presets to models
"""

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
                "stop_at_clip_layer": ("INT", {"default": -1, "min": -24, "max": -1, "step": 1}),
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
        clip_modified = clip.clone()
        clip_modified.clip_layer(stop_at_clip_layer)

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
                "stop_at_clip_layer": ("INT", {"default": -1, "min": -24, "max": -1, "step": 1}),
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
        clip_modified = clip.clone()
        clip_modified.clip_layer(stop_at_clip_layer)

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