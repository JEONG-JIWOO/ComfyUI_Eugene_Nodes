"""
LoRA Preset Management Nodes
Provides nodes for saving and selecting LoRA presets
"""

import folder_paths
import os
import json
from .helper import LoraPresetHelper


"""
Preset Editor

1. Subfolder : String List combobox
- 일단 ["none"] 만 들어가있고 추후 js를 통해 동적으로 업데이트 

2. select lora : ["none"]
- 일단 ["none"] 만 들어가있고 추후 js를 통해 동적으로 업데이트 

3. select preset : 
- 일단 ["none"] 만 들어가있고 추후 js를 통해 동적으로 업데이트 

4. "strength_model": ("FLOAT", {"default": 1.0, "min": -100.0, "max": 100.0, "step": 0.01}),
5. "strength_clip": ("FLOAT", {"default": 1.0, "min": -100.0, "max": 100.0, "step": 0.01}),

6. "preset_name_prefix": ("STRING", {"default": ""}),
7. "preset_name" : ("STRING", {"default": ""}),
8.  "P1": ("STRING", {"multiline": True, "default": ""}),
9.  "P2": ("STRING", {"multiline": True, "default": ""}),
10. "P3": ("STRING", {"multiline": True, "default": ""}),
11. "N1": ("STRING", {"multiline": True, "default": ""}),
12. "N2": ("STRING", {"multiline": True, "default": ""})
13. "N3": ("STRING", {"multiline": True, "default": ""})

14. Load From preset ("BOOLEAN", {"default": False}), (JS에서 사용하는 버튼으로 동작)
15. Load From Civitai ("BOOLEAN", {"default": False}), (JS에서 사용하는 버튼으로 동작)

Load From Civitai 구현 

https://civitai.com/api/v1/model-versions/by-hash/{SHA256 HASH}

'''
{
  "id": 1050496,
  "modelId": 706978,
  "name": "V.3",
  "createdAt": "2024-11-11T11:46:50.924Z",
  "updatedAt": "2024-11-11T11:49:42.072Z",
  "status": "Published",
  "publishedAt": "2024-11-11T11:49:42.064Z",
  "trainedWords": [
    "aesthetic_pos3",
    "dynamic_pos3"
  ],
  "trainingStatus": null,
  "trainingDetails": null,
  "baseModel": "Flux.1 D",
  "baseModelType": null,
  "earlyAccessEndsAt": null,
  "earlyAccessConfig": null,
  "description": "\u003Cp\u003ENew Triggers:\u003C/p\u003E\u003Cul\u003E\u003Cli\u003E\u003Cp\u003Eaesthetic_pos3\u003C/p\u003E\u003C/li\u003E\u003Cli\u003E\u003Cp\u003Edynamic_pos3\u003C/p\u003E\u003C/li\u003E\u003C/ul\u003E\u003Cp\u003EIn this new version of Aesthetic Poses v3, I've added new poses, enhanced realism, and trained it with models from all around the world (previously, most of the generated images were primarily of Asian models). I hope you enjoy it!\u003C/p\u003E",
  "uploadType": "Created",
  "usageControl": "Download",
  "air": "urn:air:flux1:lora:civitai:706978@1050496",
  "stats": {
    "downloadCount": 3426,
    "ratingCount": 0,
    "rating": 0,
    "thumbsUpCount": 355
  },
  "model": {
    "name": "Realistic/Aesthetic Poses FluxDev",
    "type": "LORA",
    "nsfw": false,
    "poi": false
  },
  "files": [
    {
      "id": 956231,
      "sizeKB": 167938.8828125,
      "name": "aeshteticv5.safetensors",
      "type": "Model",
      "pickleScanResult": "Success",
      "pickleScanMessage": "No Pickle imports",
      "virusScanResult": "Success",
      "virusScanMessage": null,
      "scannedAt": "2024-11-11T11:50:59.770Z",
      "metadata": {
        "format": "SafeTensor",
        "size": null,
        "fp": null
      },
      "hashes": {
        "AutoV1": "88828AE7",
        "AutoV2": "21437EC266",
        "SHA256": "21437EC26670E230B067CA936F6657CAF5CA063F15AEC333EF249BEC7C0F0DC0",
        "CRC32": "F8F2BE29",
        "BLAKE3": "AAA6F513C4BFA00031941F3A427046D31A12B161CBE2CE75AAB260C74D13C0FC",
        "AutoV3": "7AAE878CB805"
      },
      "primary": true,
      "downloadUrl": "https://civitai.com/api/download/models/1050496"
    }
  ],
  "images": [
    {
      "url": "https://image.civitai.com/xG1nkqKTMzGDvpLrqFT7WA/21bb784f-4759-4a6d-bd04-66964b87903b/width=450/39539160.jpeg",
      "nsfwLevel": 2,
      "width": 768,
      "height": 1280,
      "hash": "UOF~jNwG5QT076ngkCS$LNRj$iWYpebvxZ$*",
      "type": "image",
      "metadata": {
        "hash": "UOF~jNwG5QT076ngkCS$LNRj$iWYpebvxZ$*",
        "size": 1539987,
        "width": 768,
        "height": 1280
      },
      "meta": {
        "seed": 185666893452671,
        "vaes": [
          "ae.sft"
        ],
        "comfy": "...",
        "steps": 26,
        "models": [],
        "prompt": "aesthetic_pos3, dynamic_pos3, Retro-inspired outdoor shot of a woman on a vintage cream-colored bicycle in a sunlit garden. She wears a metallic gold swimsuit, white sneakers, and an oversized translucent orange visor, adding a futuristic touch. Surrounded by lush green trees and a clear blue sky, her relaxed pose and vibrant outfit contrast with the serene park setting, creating a playful, nostalgic vibe.",
        "denoise": 1,
        "sampler": "Euler",
        "cfgScale": 3.5,
        "modelIds": [],
        "scheduler": "simple",
        "upscalers": [],
        "versionIds": [],
        "controlNets": [],
        "additionalResources": [
          {
            "name": "aeshteticv5.safetensors",
            "type": "lora",
            "strength": 1
          }
        ]
      },
...
'''

"P1" 에 "trainedWords"  할당
"P2" 에 "images": 의 첫번째 이미지의 "meta"의  "prompt" 할당

"preset_name_prefix" : 비어있다면,  "baseModel" 할당 

"preset_name" <- "name": "Realistic/Aesthetic Poses FluxDev", -> 

그리고 Custom print 대신 직접  "Result" 위젯에 값 할당으로 접속링크인 https://civitai.com/models/${modelId} 를 출력해주자



16. Save JSon ("BOOLEAN", {"default": False}), (JS에서 사용하는 버튼으로 동작)
17. result : ("STRING", {"multiline": True, "default": ""})

Python 상에서 실행시 동작 및 리턴 : 없음. 


'''
preset json 구조 
{
    "lora_path": "SD1.5/enhance.safetensor",    // 하위호환으로 key가 "lora_name" 인 경우도 처리, windows 경로 정규화도 한번더 처리 
    "strength_model" : 1.0,                     // 하위호환으로 key가 "strength" 인 경우도 처리
    "strength_clip" : 1.0,                      // 하위호환으로 key가 "clip_strength" 인 경우도 처리
    "P1": "",                                   // 하위호환으로 key가 "prompt_positive" 인 경우도 처리
    "P2": "",                                   // 하위호환으로 key가 "sub_positive" 인 경우도 처리
    "P3": "",                                   
    "N1": "",                                   // 하위호환으로 key가 "prompt_negative" 인 경우도 처리
    "N2": "",                                   // 하위호환으로 key가 "sub_negative" 인 경우도 처리
    "N3": "",                                  
}
'''

"""

class PresetEditor:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "Subfolder": (["none"],),
                "Select LoRA": (["none"],),
                "Select Preset": (["none"],),
                "strength_model": ("FLOAT", {"default": 1.0, "min": -100.0, "max": 100.0, "step": 0.01}),
                "strength_clip": ("FLOAT", {"default": 1.0, "min": -100.0, "max": 100.0, "step": 0.01}),
                "preset_name_prefix": ("STRING", {"default": ""}),
                "preset_name": ("STRING", {"default": ""}),
                "P1": ("STRING", {"multiline": True, "default": ""}),
                "P2": ("STRING", {"multiline": True, "default": ""}),
                "P3": ("STRING", {"multiline": True, "default": ""}),
                "N1": ("STRING", {"multiline": True, "default": ""}),
                "N2": ("STRING", {"multiline": True, "default": ""}),
                "N3": ("STRING", {"multiline": True, "default": ""}),
                "Load From Preset": ("BOOLEAN", {"default": False}),
                "Load From Civitai": ("BOOLEAN", {"default": False}),
                "Save JSON": ("BOOLEAN", {"default": False}),
                "Refresh": ("BOOLEAN", {"default": False}),
                "Result": ("STRING", {"multiline": True, "default": ""}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "process"

    CATEGORY = "LoRA Tools"

    def process(
        self,
        Subfolder,
        Select_LoRA,
        Select_Preset,
        strength_model,
        strength_clip,
        preset_name_suffix,
        preset_name,
        P1, P2, P3, N1, N2, N3,
        Load_From_Preset,
        Load_From_Civitai,
        Save_JSON
    ):
        """이 노드는 UI에서 프리셋을 선택하고 수정하는 역할만 수행하며, 실제 실행은 하지 않음"""

        result = f"Preset: {Subfolder}{preset_name_suffix}{preset_name}\n" \
                 f"Strength Model: {strength_model}, Strength Clip: {strength_clip}\n" \
                 f"P1: {P1}\nP2: {P2}\nP3: {P3}\n" \
                 f"N1: {N1}\nN2: {N2}\nN3: {N3}\n"

        return (result,)

class PresetSaver:
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