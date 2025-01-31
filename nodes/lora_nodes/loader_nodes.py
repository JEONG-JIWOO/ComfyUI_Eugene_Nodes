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


"""DictBasedLoraLoader - LoRA 모델 로더 및 프롬프트 처리 노드

lora_dict 구조:
{
   "lora_info": {
       "별명": [파일경로, 표시명, 강도, 클립강도, [유효키워드리스트]],
   },
   "lora_keywards": {
       "별명_P/N/SP/SN": "프롬프트내용",
   }
}
"""


class DictBasedLoraLoader:
    loaded_loras = {}  # 로딩된 LoRA 캐시

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "positive_prefix": ("STRING", {"multiline": True}),  # 양성 프롬프트 접두사
                "positive_suffix": ("STRING", {"multiline": True}),  # 양성 프롬프트 접미사
                "negative_prefix": ("STRING", {"multiline": True}),  # 음성 프롬프트 접두사
                "negative_suffix": ("STRING", {"multiline": True}),  # 음성 프롬프트 접미사
                "stop_at_clip_layer": ("INT", {"default": -1, "min": -24, "max": 0, "step": 1}),  # CLIP 모델 레이어 제한
            },
            "optional": {
                "input_dictionary": ("DICT",),  # 추가 키워드 사전
                "model": ("MODEL",),  # 기본 모델
                "clip": ("CLIP",),  # CLIP 모델
                "vae": ("VAE",),  # VAE 모델
                "basic_pipe": ("BASIC_PIPE",),  # 기본 파이프라인
                "dict_bus": ("DICT_BUS",),  # 사전 버스
                "lora_dict": ("DICT",),  # LoRA 사전
                "do_conditioning": ("BOOLEAN", {"default": True}),  # 컨디셔닝 수행 여부
            }
        }

    RETURN_TYPES = ("DICT", "MODEL", "CLIP", "VAE", "CONDITIONING", "CONDITIONING", "BASIC_PIPE", "STRING", "STRING")
    RETURN_NAMES = ("input_dict", "model", "clip", "vae", "positive_conditioning", "negative_conditioning",
                    "basic_pipe", "positive_prompt", "negative_prompt")
    FUNCTION = "process_loras"
    CATEGORY = "lora/loader"

    def process_loras(self, positive_prefix, positive_suffix, negative_prefix, negative_suffix,
                      stop_at_clip_layer, input_dictionary={}, model=None, clip=None, vae=None,
                      basic_pipe=None, dict_bus=None, lora_dict=None, do_conditioning=True):
        """LoRA 모델 로드 및 프롬프트 처리

        처리 단계:
        1. 입력 모델 초기화 - dict_bus나 basic_pipe에서 모델 불러오기
        2. LoRA 모델 로드 - 유효 키워드가 있는 LoRA만 로드
        3. 프롬프트 처리 - 입력 사전과 LoRA 키워드를 통합하여 치환
        4. 컨디셔닝 생성 - 최종 프롬프트로 CLIP 인코딩
        """

        # 1. 입력 모델 초기화
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

        # CLIP 모델 레이어 제한 설정
        clip_modified = clip.clone()
        if stop_at_clip_layer < 0:
            clip_modified.clip_layer(stop_at_clip_layer)

        # 2. LoRA 모델 로드

        # 키워드 존재 검사를 위한 전체프름프트
        total_prompts = [positive_prefix, negative_prefix, positive_suffix, negative_suffix]

        if lora_dict and "lora_info" in lora_dict:
            for alias, info in lora_dict["lora_info"].items():
                path, _, strength, clip_strength, prompt_keys = info
                # 유효 키워드가 있는 LoRA만 로드
                if prompt_keys and path and path != "none":
                    if self.has_prompting_keys(total_prompts,prompt_keys):
                        try:
                            model, clip_modified = LoraPresetHelper.load_and_apply_lora(
                                self.loaded_loras, model, clip_modified,
                                path, strength, clip_strength
                            )
                        except Exception as e:
                            print(f"Error loading LoRA {alias}: {str(e)}")

        # 3. 프롬프트 처리
        combined_dict = dict(input_dictionary or {})
        if lora_dict and "lora_keywards" in lora_dict:
            combined_dict.update(lora_dict["lora_keywards"])

        # 프롬프트 키워드 치환
        pos_prefix = LoraPresetHelper.replace_dict_keys(positive_prefix, combined_dict)
        neg_prefix = LoraPresetHelper.replace_dict_keys(negative_prefix, combined_dict)
        pos_suffix = LoraPresetHelper.replace_dict_keys(positive_suffix, combined_dict)
        neg_suffix = LoraPresetHelper.replace_dict_keys(negative_suffix, combined_dict)

        # 최종 프롬프트 생성
        positive_prompt = LoraPresetHelper.clean_prompt(f"{pos_prefix}, {pos_suffix}")
        negative_prompt = LoraPresetHelper.clean_prompt(f"{neg_prefix}, {neg_suffix}")

        # 4. 컨디셔닝 생성
        positive_conditioning = None
        negative_conditioning = None

        if do_conditioning:
            try:
                positive_conditioning = LoraPresetHelper.encode_prompt(clip_modified, positive_prompt)
                negative_conditioning = LoraPresetHelper.encode_prompt(clip_modified, negative_prompt)
            except Exception as e:
                print(f"Error encoding prompts: {str(e)}")

        # 기본 파이프라인 구성
        basic_pipe = (model, clip, vae, positive_conditioning, negative_conditioning)

        return (input_dictionary, model, clip_modified, vae, positive_conditioning, negative_conditioning,
                basic_pipe, positive_prompt, negative_prompt)

    def has_prompting_keys(self, prompts, prompt_keys):
        """프롬프트들에 키워드가 포함되어 있는지 검사"""
        combined_text = ", ".join(filter(None, prompts))
        return any(f"{{{key}}}" in combined_text for key in prompt_keys)