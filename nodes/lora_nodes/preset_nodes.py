"""
LoRA Preset Management Nodes
Provides nodes for saving and selecting LoRA presets
"""

import folder_paths
import os
import json
from .helper import LoraPresetHelper


"""
## Preset Editor 노드의 입력 항목 설명:
 1. Subfolder: 문자열 리스트 콤보박스. 초기 값은 ["none"]이며, 나중에 JS를 통해 동적으로 업데이트 됩니다.
 2. Select LoRA: ["none"] (추후 동적 업데이트)
 3. Select Preset: ["none"] (추후 동적 업데이트)
 4. strength_model: 실수형 (기본값 1.0, 범위 -100.0 ~ 100.0, step 0.01)
 5. strength_clip: 실수형 (기본값 1.0, 범위 -100.0 ~ 100.0, step 0.01)
 6. preset_name_prefix: 문자열 (기본값 빈 문자열)
 7. preset_name: 문자열 (기본값 빈 문자열)
 8 ~ 10. P1, P2, P3: 문자열 (멀티라인, 기본값 빈 문자열)
 11 ~ 13. N1, N2, N3: 문자열 (멀티라인, 기본값 빈 문자열)
 14. Load From Preset: 불리언 (기본값 False, 버튼 역할)
 15. Load From Civitai: 불리언 (기본값 False, 버튼 역할)
     - 해당 버튼 클릭 시 civitai API를 호출하여 로라 파일의 해시를 기반으로 데이터를 가져오고,
       가져온 데이터로 P1, P2, preset_name_prefix, preset_name, 그리고 Result 위젯에 값을 할당합니다.
 16. Save JSON: 불리언 (기본값 False, 버튼 역할, 프리셋 JSON 저장)
 17. Result: 문자열 (멀티라인, 결과 출력)
 
 프리셋 JSON의 구조는 하위 호환성을 고려하여 여러 키를 처리합니다.

### Load From Civitai 구현 
https://civitai.com/api/v1/model-versions/by-hash/{SHA256 HASH}
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
  ...
  "images": [],
}

- "P1" 에 "trainedWords"  할당
- [비활성화] "P2" 에 "images": 의 첫번째 이미지의 "meta"의  "prompt" 할당 
- "preset_name_prefix" : 비어있다면,  "baseModel" 할당 
- "preset_name" <- "model" , "name": 할당

### preset json 구조 
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

"""

class PresetEditor:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # Subfolder 선택 콤보박스
                "Subfolder": (["none"],),
                # 로라 파일 선택 콤보박스
                "Select LoRA": (["none"],),
                # 프리셋 파일 선택 콤보박스
                "Select Preset": (["none"],),
                # 로라 모델의 strength 값 (모델에 적용되는 strength)
                "strength_model": ("FLOAT", {"default": 1.0, "min": -100.0, "max": 100.0, "step": 0.01}),
                # 클립 모델에 적용되는 strength 값
                "strength_clip": ("FLOAT", {"default": 1.0, "min": -100.0, "max": 100.0, "step": 0.01}),
                # 프리셋 이름 접두사 (비어있으면 나중에 civitai의 baseModel 값을 할당)
                "preset_name_prefix": ("STRING", {"default": ""}),
                # 프리셋 이름 (파일명에서 확장자 제거한 값 또는 civitai model.name)
                "preset_name": ("STRING", {"default": ""}),
                # 양수 프롬프트 관련 값들 (P1, P2, P3)
                "P1": ("STRING", {"multiline": True, "default": ""}),
                "P2": ("STRING", {"multiline": True, "default": ""}),
                "P3": ("STRING", {"multiline": True, "default": ""}),
                # 음수 프롬프트 관련 값들 (N1, N2, N3)
                "N1": ("STRING", {"multiline": True, "default": ""}),
                "N2": ("STRING", {"multiline": True, "default": ""}),
                "N3": ("STRING", {"multiline": True, "default": ""}),
                # Load From Preset 버튼 (JS에서 동작하여 프리셋 JSON을 불러옴)
                "Load From Preset": ("BOOLEAN", {"default": False}),
                # Load From Civitai 버튼 (JS에서 동작하여 civitai 데이터를 가져옴)
                "Load From Civitai": ("BOOLEAN", {"default": False}),
                # Save JSON 버튼 (프리셋 데이터를 저장)
                "Save JSON": ("BOOLEAN", {"default": False}),
                # Refresh 버튼 (서브폴더 목록을 갱신)
                "Refresh": ("BOOLEAN", {"default": False}),
                # 결과 출력을 위한 위젯
                "Result": ("STRING", {"multiline": True, "default": ""}),
            },
            "optional": {},
        }

    # 노드 실행 결과는 문자열 하나를 리턴함
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
        preset_name_suffix,  # UI에서는 preset_name_suffix 라고 불리지만, 내부적으로는 preset_name과 결합
        preset_name,
        P1, P2, P3, N1, N2, N3,
        Load_From_Preset,
        Load_From_Civitai,
        Save_JSON
    ):
        """
        이 노드는 UI에서 프리셋을 선택하고 수정하는 역할만 수행합니다.
        실제 실행은 하지 않고, 단순히 선택된 값들을 문자열로 출력하여 결과 위젯에 반영합니다.
        """
        # 선택된 값들을 포맷팅하여 문자열 결과 생성
        result = f"Preset: {Subfolder}{preset_name_suffix}{preset_name}\n" \
                 f"Strength Model: {strength_model}, Strength Clip: {strength_clip}\n" \
                 f"P1: {P1}\nP2: {P2}\nP3: {P3}\n" \
                 f"N1: {N1}\nN2: {N2}\nN3: {N3}\n"

        return (result,)

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
  - 프롬프트타입: P1, P2,P3, N1,N2,N3
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
            ["anime_P1", "anime_P2"]  # 유효한 프롬프트만 포함
        ]
    },
    "lora_keywards": {
        "anime_P1": "masterpiece, best quality",
        "anime_S2": "beautiful anime style"
    }
}
```
"""

import json


# PresetSelectorV2 노드는 LoRA 프리셋 관리 딕셔너리(lora_info, lora_keywards)를 생성합니다.
# 프리셋 JSON 구조는 아래와 같이 변경되었습니다.
# {
#     "lora_path": "SD1.5/enhance.safetensor",    // 하위호환: "lora_name"도 처리, 윈도우 경로 정규화
#     "strength_model" : 1.0,                      // 하위호환: "strength"도 처리
#     "strength_clip" : 1.0,                       // 하위호환: "clip_strength"도 처리
#     "P1": "",                                    // 하위호환: "prompt_positive"도 처리
#     "P2": "",                                    // 하위호환: "sub_positive"도 처리
#     "P3": "",
#     "N1": "",                                    // 하위호환: "prompt_negative"도 처리
#     "N2": "",                                    // 하위호환: "sub_negative"도 처리
#     "N3": "",
# }
#
# 또한, 기존에 js에서 전달받던 복잡한 display_name 대신
# js에서는 이제 subfolder를 포함한 preset JSON 이름(즉, preset_path)를 그대로 전달합니다.
#
# 참고: 여기서는 helper 함수(LoraPresetHelper.*)를 그대로 사용하되,
#       출력된 preset_data의 키 이름(예:"P1", "P2", 등)을 기준으로 동작하도록 수정합니다.

class PresetSelectorV2:
    all_subfolders = []
    all_presets = []

    @classmethod
    def INPUT_TYPES(cls):
        # 최초 데이터 초기화 (노드 로드시 서브폴더 및 프리셋 목록을 채웁니다)
        if not cls.all_subfolders:
            cls.initialize_data()

        return {
            "required": {
                # 사용 가능한 서브폴더 목록 (helper를 통해 초기화)
                "subfolder": (cls.all_subfolders,),
                # LoRA 별칭(별명) 입력. 최종 lora_info의 key로 사용됩니다.
                "Alias": ("STRING", {"default": "lora1"}),
                # weight(강도) 값을 덮어쓸지 여부 (True이면 입력된 strength/clip_strength 사용)
                "override_weights": ("BOOLEAN", {"default": False}),
                # override가 False인 경우 프리셋에 저장된 값 사용, True면 이 값을 사용
                "strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                "clip_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                # bypass가 True면 프리셋 로드 작업을 건너뛰고 그대로 결과 딕셔너리를 리턴함
                "bypass": ("BOOLEAN", {"default": False}),
                # refresh가 True면 내부 데이터(서브폴더/프리셋 목록)를 갱신함
                "refresh": ("BOOLEAN", {"default": False}),
                # output_loras: js에서 할당한 preset json 이름(이제 subfolder 포함 preset json 이름)
                # JSON 형식의 문자열 예: '["SD1.5/my_preset.json"]'
                "output_loras": ("STRING", {"default": "[]"})
            },
            "optional": {
                # 기존 딕셔너리를 전달받으면 그대로 사용, 없으면 새로 생성
                "input_lora_dict": ("DICT",)
            }
        }

    RETURN_TYPES = ("DICT",)
    RETURN_NAMES = ("selected_lora_dict",)
    FUNCTION = "select_preset"
    CATEGORY = "lora/preset"

    @classmethod
    def initialize_data(cls):
        """노드가 로드될 때 서브폴더와 프리셋 목록을 초기화합니다."""
        cls.all_subfolders = LoraPresetHelper.get_subfolder_list()
        cls.all_presets = LoraPresetHelper.list_presets()
        # cls.all_presets는 원래 (preset_path, display_name) 튜플 리스트였으나,
        # 이제 display_name은 사용되지 않고 preset_path(즉, subfolder를 포함한 프리셋 JSON 이름)가 전달됩니다.

    @classmethod
    def update_data(cls):
        """데이터 갱신 함수 (노드 외부에서 호출할 수 있음)"""
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
        """
        프리셋을 선택하여 LoRA 관리 딕셔너리(lora_info, lora_keywards)를 생성합니다.

        - bypass가 True이면 작업을 건너뛰고 그대로 결과 딕셔너리를 반환합니다.
        - output_loras는 js에서 전달한 preset json 이름(이제 subfolder를 포함한 preset json 이름)입니다.
        - 프리셋 JSON에서 새 구조에 따라 lora_path, strength_model, strength_clip, P1, P2, P3, N1, N2, N3 키를 사용합니다.
        - 유효한 프롬프트 텍스트(P1~N3)가 있으면 해당 키워드를 lora_keywards 딕셔너리에 저장하고, 그 키 목록을 lora_info에도 저장합니다.
        """
        # refresh가 True면 데이터 갱신
        if refresh:
            self.update_data()

        # input_lora_dict가 이미 전달되었으면 그대로 사용, 없으면 새 딕셔너리 생성
        if input_lora_dict:
            result = input_lora_dict
        else:
            result = {
                "lora_info": {},
                "lora_keywards": {}
            }

        # bypass가 True이면 바로 결과를 반환합니다.
        if bypass:
            return (result,)

        try:
            # output_loras는 이제 preset json 이름(서브폴더 포함)이 담긴 JSON 문자열입니다.
            display_names = json.loads(output_loras)
            if not display_names:
                return (result,)

            # 이제 첫 번째 요소가 preset_path (즉, subfolder 포함 preset json 이름)
            preset_path = display_names[0]
            # preset_path를 기반으로 프리셋 데이터를 로드합니다.
            preset_data = LoraPresetHelper.load_preset_data().get(preset_path)
            if preset_data is None:
                print(f"Warning: No preset data found for: {preset_path}")
                return (result,)

            # 새로운 LoRA 엔트리 생성
            # 프리셋 데이터에서 lora_path, strength_model, strength_clip 값을 추출합니다.
            # 하위호환 처리를 위해 "lora_path" 없으면 "lora_name"을, "strength_model" 없으면 "strength"를, "strength_clip" 없으면 "clip_strength"를 사용합니다.
            lora_path = preset_data.get("lora_path") or preset_data.get("lora_name", "")
            preset_strength = preset_data.get("strength_model") or preset_data.get("strength", 1.0)
            preset_clip_strength = preset_data.get("strength_clip") or preset_data.get("clip_strength", 1.0)

            # 만약 override_weights가 True이면 입력된 strength, clip_strength 사용
            final_strength = strength if override_weights else preset_strength
            final_clip_strength = clip_strength if override_weights else preset_clip_strength

            # 프롬프트 키워드를 저장할 리스트 (lora_info의 5번째 요소)
            prompt_keys = []

            # lora_info의 두 번째 요소(표시명)는 더 이상 별도의 display_name이 없으므로, preset_path를 그대로 사용합니다.
            result["lora_info"][Alias] = [
                lora_path,  # 파일 경로
                preset_path,  # 표시명 대신 preset_path 사용
                final_strength,  # 적용 강도
                final_clip_strength,  # 클립 강도
                prompt_keys  # 유효 프롬프트 키워드 목록 (나중에 추가)
            ]

            # 프리셋 JSON에서 프롬프트 텍스트를 추출합니다.
            # 새 구조에 따라 키는 "P1", "P2", "P3", "N1", "N2", "N3" 입니다.
            if p1 := preset_data.get("P1"):
                prompt_keys.append(f"{Alias}_P1")
                result["lora_keywards"][f"{Alias}_P1"] = p1

            if p2 := preset_data.get("P2"):
                prompt_keys.append(f"{Alias}_P2")
                result["lora_keywards"][f"{Alias}_P2"] = p2

            if p3 := preset_data.get("P3"):
                prompt_keys.append(f"{Alias}_P3")
                result["lora_keywards"][f"{Alias}_P3"] = p3

            if n1 := preset_data.get("N1"):
                prompt_keys.append(f"{Alias}_N1")
                result["lora_keywards"][f"{Alias}_N1"] = n1

            if n2 := preset_data.get("N2"):
                prompt_keys.append(f"{Alias}_N2")
                result["lora_keywards"][f"{Alias}_N2"] = n2

            if n3 := preset_data.get("N3"):
                prompt_keys.append(f"{Alias}_N3")
                result["lora_keywards"][f"{Alias}_N3"] = n3

            return (result,)

        except json.JSONDecodeError:
            print(f"Error decoding output_loras JSON: {output_loras}")
            return (result,)
        except Exception as e:
            print(f"Error in select_preset: {str(e)}")
            return (result,)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # 데이터 갱신 여부를 판단하기 위해 항상 True를 반환합니다.
        cls.initialize_data()
        return True
