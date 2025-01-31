"""
LoRA Preset Management Nodes
Provides nodes for saving and selecting LoRA presets
"""

import folder_paths
import os
import json
from .helper import LoraPresetHelper


class SinglePresetSaver:
    @classmethod
    def INPUT_TYPES(cls):
        lora_files = folder_paths.get_filename_list("loras")
        return {
            "required": {
                "triggered": ("BOOLEAN", {"default": False}),
                "lora_name": (["none"] + lora_files,),
                "strength": ("FLOAT", {"default": 1.0, "min": -100.0, "max": 100.0, "step": 0.01}),
                "clip_strength": ("FLOAT", {"default": 1.0, "min": -100.0, "max": 100.0, "step": 0.01}),
                "suffix": ("STRING", {"default": ""}),
                "nickname": ("STRING", {"default": ""}),
            },
            "optional": {
                "prompt_positive": ("STRING", {"multiline": True, "default": ""}),
                "prompt_negative": ("STRING", {"multiline": True, "default": ""}),
                "sub_positive": ("STRING", {"multiline": True, "default": ""}),
                "sub_negative": ("STRING", {"multiline": True, "default": ""})
            }
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "save_preset"
    CATEGORY = "lora/preset"

    def save_preset(self, triggered, lora_name, strength, clip_strength, suffix, nickname,
                    prompt_positive="", prompt_negative="", sub_positive="", sub_negative=""):
        if not triggered or lora_name == "none":
            return ("LoRA preset not saved. Set 'triggered' to True and select a LoRA.",)

        preset_name = os.path.splitext(lora_name)[0]
        lora_data = {
            "lora_name": lora_name,
            "lora_path": os.path.join(LoraPresetHelper.get_lora_folder_path(), lora_name),
            "strength": strength,
            "clip_strength": clip_strength,
            "prompt_positive": prompt_positive,
            "prompt_negative": prompt_negative,
            "sub_positive": sub_positive,
            "sub_negative": sub_negative,
        }

        saved_file = LoraPresetHelper.save_preset(preset_name, lora_data, suffix, nickname)
        return (f"LoRA preset saved to: {saved_file}",)


"""
# ComfyUI LoRA 프리셋 관리 딕셔너리 구조

## 기본 구조
```python
{
    "lora_info": {
        "별명": [파일경로, 표시명, 강도, 클립강도, [유효키워드리스트]],
        ...
    },
    "lora_keywards": {
        "키워드": "프롬프트내용",
        ...
    }  
}
```

## lora_info
- 키: LoRA의 식별자로 사용할 별명 (예: "chilloutmix", "animeHQ")
- 값: 리스트 형태로 LoRA 기본 정보 저장
  1. 파일경로: LoRA 모델 파일 위치
  2. 표시명: UI에 표시될 이름
  3. 강도: LoRA 적용 강도 (기본값 1.0)
  4. 클립강도: CLIP 모델 적용 강도 (기본값 1.0)
  5. 유효키워드리스트: 해당 LoRA의 유효한 프롬프트 키워드 목록

## lora_keywards
- 키: `{별명}_{프롬프트타입}` 형식의 키워드
  - 프롬프트타입: P(positive), N(negative), SP(sub_positive), SN(sub_negative)
- 값: 실제 프롬프트 텍스트
- 빈 문자열이나 누락된 프롬프트는 포함하지 않음

## 사용 예시
```python
{
    "lora_info": {
        "anime": [
            "/loras/anime.safetensors",
            "Anime Style LoRA",
            0.8,
            0.7,
            ["anime_P", "anime_SP"]  # 유효한 프롬프트만 포함
        ]
    },
    "lora_keywards": {
        "anime_P": "masterpiece, best quality",
        "anime_SP": "beautiful anime style"
    }
}
```
"""

class PresetSelectorV2:
    all_subfolders = []
    all_presets = []

    @classmethod
    def INPUT_TYPES(cls):
        if not cls.all_subfolders:
            cls.initialize_data()

        return {
            "required": {
                "subfolder": (cls.all_subfolders,),
                "Alias": ("STRING", {"default": "lora1"}),
                "override_weights": ("BOOLEAN", {"default": False}),
                "strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                "clip_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                "bypass": ("BOOLEAN", {"default": False}),
                "refresh": ("BOOLEAN", {"default": False}),
                "output_loras": ("STRING", {"default": "[]"})  # JSON string of display_names
            },
            "optional": {
                "input_lora_dict": ("DICT",)
            }
        }

    RETURN_TYPES = ("DICT",)
    RETURN_NAMES = ("selected_lora_dict",)
    FUNCTION = "select_preset"
    CATEGORY = "lora/preset"

    @classmethod
    def initialize_data(cls):
        """Initialize all data when node is loaded"""
        cls.all_subfolders = LoraPresetHelper.get_subfolder_list()
        cls.all_presets = LoraPresetHelper.list_presets()

    @classmethod
    def update_data(cls):
        """Update data method"""
        cls.initialize_data()
        return {
            "subfolders": cls.all_subfolders,
            "presets": [
                {"path": path, "display_name": display_name}
                for path, display_name in cls.all_presets
            ]
        }

    def select_preset(self, subfolder, Alias, override_weights, strength, clip_strength,
                      bypass, refresh, output_loras, input_lora_dict=None):
        """Select preset and return restructured lora dictionary"""
        if refresh:
            self.update_data()

        if input_lora_dict:
            result = input_lora_dict
        else :
            result = {
                "lora_info": {},
                "lora_keywards": {}
            }

        if bypass:
            return (result,)

        try:
            display_names = json.loads(output_loras)
            if not display_names:
                return (result,)

            display_name = display_names[0]
            preset_path = next((path for path, name in self.all_presets if name == display_name), None)

            if preset_path is None:
                print(f"Warning: No matching preset found for display_name: {display_name}")
                return (result,)

            preset_data = LoraPresetHelper.load_preset_data().get(preset_path)
            if preset_data is None:
                print(f"Warning: No preset data found for: {preset_path}")
                return (result,)

            # 새로운 lora 엔트리 생성
            prompt_keys = []
            result["lora_info"][Alias] = [
                preset_path,
                display_name,
                strength if override_weights else preset_data.get("strength", 1.0),
                clip_strength if override_weights else preset_data.get("clip_strength", 1.0),
                prompt_keys
            ]

            # 유효한 프롬프트 검사 및 저장
            if p := preset_data.get("prompt_positive"):
                prompt_keys.append(f"{Alias}_P")
                result["lora_keywards"][f"{Alias}_P"] = p

            if n := preset_data.get("prompt_negative"):
                prompt_keys.append(f"{Alias}_N")
                result["lora_keywards"][f"{Alias}_N"] = n

            if sp := preset_data.get("sub_positive"):
                prompt_keys.append(f"{Alias}_SP")
                result["lora_keywards"][f"{Alias}_SP"] = sp

            if sn := preset_data.get("sub_negative"):
                prompt_keys.append(f"{Alias}_SN")
                result["lora_keywards"][f"{Alias}_SN"] = sn

            return (result,)

        except json.JSONDecodeError:
            print(f"Error decoding output_loras JSON: {output_loras}")
            return (result,)
        except Exception as e:
            print(f"Error in select_preset: {str(e)}")
            return (result,)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        cls.initialize_data()
        return True