# Core Dictionary Management Nodes
import os
import json
import random
import folder_paths
from pathlib import Path
from typing import Dict, Tuple, Any

class DictUpdateBase:
    """Base class for dictionary update nodes to reduce duplication"""
    @classmethod
    def create_input_types(cls, num_inputs: int):
        inputs = {
            "required": {},
            "optional": {
                "input_dict": ("DICT",),
            }
        }
        
        # Add key-value pairs based on num_inputs
        for i in range(1, num_inputs + 1):
            key_name = f"key{i}" if num_inputs > 1 else "key"
            val_name = f"value{i}" if num_inputs > 1 else "value"
            
            inputs["optional" if num_inputs > 1 else "required"][key_name] = ("STRING", {"default": ""})
            inputs["optional" if num_inputs > 1 else "required"][val_name] = ("STRING", {"multiline": True})
            
        return inputs

    def update_dict_common(self, input_dict=None, **kwargs) -> Tuple[Dict]:
        result_dict = input_dict.copy() if input_dict else {}
        
        # Extract pairs dynamically based on kwargs
        # This handles both key/value and key1/value1, key2/value2... patterns
        
        # Check for single key/value pattern
        if "key" in kwargs and "value" in kwargs:
            k, v = kwargs["key"], kwargs["value"]
            if k and v:
                result_dict[k] = v.strip()
                
        # Check for numbered patterns
        for i in range(1, 11): 
            k = kwargs.get(f"key{i}")
            v = kwargs.get(f"value{i}")
            if k and v:
                result_dict[k] = v.strip()
                
        return (result_dict,)

class DictUpdate1(DictUpdateBase):
    @classmethod
    def INPUT_TYPES(cls):
        return cls.create_input_types(1)

    RETURN_TYPES = ("DICT",)
    FUNCTION = "update_dict"
    CATEGORY = "dictionary/core"

    def update_dict(self, key, value, input_dict=None):
        return self.update_dict_common(input_dict, key=key, value=value)


class DictUpdate5(DictUpdateBase):
    @classmethod
    def INPUT_TYPES(cls):
        return cls.create_input_types(5)

    RETURN_TYPES = ("DICT",)
    FUNCTION = "update_dict"
    CATEGORY = "dictionary/core"

    def update_dict(self, input_dict=None, **kwargs):
        return self.update_dict_common(input_dict, **kwargs)


class DictUpdate10(DictUpdateBase):
    @classmethod
    def INPUT_TYPES(cls):
        return cls.create_input_types(10)

    RETURN_TYPES = ("DICT",)
    FUNCTION = "update_dict"
    CATEGORY = "dictionary/core"

    def update_dict(self, input_dict=None, **kwargs):
        return self.update_dict_common(input_dict, **kwargs)


# Dictionary Utility Nodes
class DictTemplate:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "template_text": ("STRING", {"multiline": True}),
                "dictionary": ("DICT", {})
            }
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "apply_template"
    CATEGORY = "dictionary/utils"

    def apply_template(self, template_text: str, dictionary: Dict) -> Tuple[str]:
        try:
            result = template_text
            for key, value in dictionary.items():
                placeholder = "{" + str(key) + "}"
                result = result.replace(placeholder, str(value))
            return (result,)
        except Exception as e:
            print(f"Error processing template: {str(e)}")
            return (template_text,)


class DictMultilineSelect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_dict": ("DICT", {}),
                "line_number": ("INT", {"default": 0, "min": 0, "max": 9999}),
                "multiline_text": ("STRING", {"multiline": True}),
                "key_string": ("STRING", {})
            }
        }

    RETURN_TYPES = ("DICT", "INT")
    FUNCTION = "select_line"
    CATEGORY = "dictionary/utils"

    def select_line(self, input_dict: Dict, line_number: int, multiline_text: str, key_string: str) -> Tuple[Dict, int]:
        result_dict = dict(input_dict)
        lines = multiline_text.split('\n')

        if line_number >= len(lines):
            raise ValueError(f"Line number {line_number} is out of range. Text has {len(lines)} lines.")

        selected_line = lines[line_number].strip()
        result_dict[key_string] = selected_line

        return (result_dict, line_number)

class DictJSONSave:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "dictionary": ("DICT", {}),
                "filename": ("STRING", {"default": "dictionary"})
            }
        }

    RETURN_TYPES = ("DICT",)
    FUNCTION = "save_dict"
    CATEGORY = "dictionary/json"

    def save_dict(self, dictionary: Dict, filename: str) -> Tuple[Dict]:
        # Ensure the directory exists
        save_dir = Path("./dictionary_json")
        save_dir.mkdir(exist_ok=True)

        # Add .json extension if not present
        if not filename.endswith('.json'):
            filename += '.json'

        # Full path for saving
        save_path = save_dir / filename

        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(dictionary, f, ensure_ascii=False, indent=2)
            print(f"Dictionary saved to {save_path}")
        except Exception as e:
            print(f"Error saving dictionary: {str(e)}")

        return (dictionary,)


class DictJSONLoad:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "filename": (s.get_available_files(),),
            }
        }

    RETURN_TYPES = ("DICT",)
    FUNCTION = "load_dict"
    CATEGORY = "dictionary/json"

    @classmethod
    def get_available_files(cls):
        # Get list of JSON files in the directory
        save_dir = Path("./dictionary_json")
        if not save_dir.exists():
            return []

        files = [f.name for f in save_dir.glob("*.json")]
        return sorted(files)

    def load_dict(self, filename: str) -> Tuple[Dict]:
        load_path = Path("./dictionary_json") / filename

        try:
            with open(load_path, 'r', encoding='utf-8') as f:
                loaded_dict = json.load(f)
            print(f"Dictionary loaded from {load_path}")
        except Exception as e:
            print(f"Error loading dictionary: {str(e)}")
            loaded_dict = {}

        return (loaded_dict,)

class XMLTagExtractor:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_text": ("STRING", {"multiline": True}),
                "tag1": ("STRING", {"default": "tag"}),
            },
            "optional": {
                "tag2": ("STRING", {"default": ""}),
                "tag3": ("STRING", {"default": ""}),
                "tag4": ("STRING", {"default": ""}),
                "input_dict": ("DICT",),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "DICT",)
    RETURN_NAMES = ("tag1_content", "tag2_content", "tag3_content", "tag4_content", "updated_dict",)
    FUNCTION = "extract_tags"
    CATEGORY = "dictionary/utils"

    def extract_tags(self, input_text: str, tag1: str, tag2: str="", tag3: str="", tag4: str="", input_dict: Dict=None) -> Tuple[str, str, str, str, Dict]:
        tag1_content = ""
        tag2_content = ""
        tag3_content = ""
        tag4_content = ""
        
        # Create a copy of the input dictionary or initialize a new one
        result_dict = input_dict.copy() if input_dict else {}
        
        # Extract content from tags and update dictionary
        for tag, content_var in [
            (tag1, "tag1_content"), 
            (tag2, "tag2_content"), 
            (tag3, "tag3_content"), 
            (tag4, "tag4_content")
        ]:
            if tag:
                open_tag = f"<{tag}>"
                close_tag = f"</{tag}>"
                
                start_pos = input_text.find(open_tag)
                if start_pos != -1:
                    start_pos += len(open_tag)
                    end_pos = input_text.find(close_tag, start_pos)
                    if end_pos != -1:
                        extracted_content = input_text[start_pos:end_pos].strip()
                        
                        # Set the appropriate content variable
                        if content_var == "tag1_content":
                            tag1_content = extracted_content
                        elif content_var == "tag2_content":
                            tag2_content = extracted_content
                        elif content_var == "tag3_content":
                            tag3_content = extracted_content
                        elif content_var == "tag4_content":
                            tag4_content = extracted_content
                        
                        # Update the dictionary with the tag as key and extracted content as value
                        result_dict[tag] = extracted_content
        
        return (tag1_content, tag2_content, tag3_content, tag4_content, result_dict,)


class JSONFileSelector:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder_path": ("STRING", {"default": ""}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            },
        }
    
    RETURN_TYPES = ("STRING",)
    FUNCTION = "select_json_file"
    CATEGORY = "utils"

    def select_json_file(self, folder_path, seed):
        # 폴더 경로가 존재하는지 확인
        if not os.path.exists(folder_path):
            raise ValueError(f"폴더 경로가 존재하지 않습니다: {folder_path}")
        
        # 폴더 내 모든 JSON 파일 찾기
        json_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.json')]
        
        if not json_files:
            raise ValueError(f"지정된 폴더에 JSON 파일이 없습니다: {folder_path}")
        
        # 시드 기반 해시 계산 및 파일 선택
        rng = random.Random(seed)
        
        # 각 파일에 대해 해시 값 계산
        file_hashes = []
        for filename in json_files:
            # 파일 이름과 시드를 조합하여 결정론적 해시 생성
            file_seed = hash((filename, seed)) % 0xffffffffffffffff
            file_rng = random.Random(file_seed)
            hash_value = file_rng.random()
            file_hashes.append((filename, hash_value))
        
        # 해시 값으로 정렬
        file_hashes.sort(key=lambda x: x[1])
        
        # 가장 낮은 해시 값을 가진 파일 선택
        selected_file = file_hashes[0][0]
        file_path = os.path.join(folder_path, selected_file)
        
        print(f"선택된 JSON 파일: {selected_file} (시드: {seed})")
        
        return (file_path,)


class DictSaveToFolder:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "dictionary": ("DICT", {}),
                "folder_path": ("STRING", {"default": "./custom_dicts"}),
                "filename": ("STRING", {"default": "dictionary"})
            }
        }

    RETURN_TYPES = ("DICT",)
    FUNCTION = "save_dict_to_folder"
    CATEGORY = "dictionary/json"

    def save_dict_to_folder(self, dictionary, folder_path, filename):
        # 폴더 경로 생성
        save_dir = Path(folder_path)
        save_dir.mkdir(exist_ok=True, parents=True)

        # .json 확장자 추가
        if not filename.endswith('.json'):
            filename += '.json'

        # 저장 경로
        save_path = save_dir / filename

        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(dictionary, f, ensure_ascii=False, indent=2)
            print(f"Dictionary saved to {save_path}")
        except Exception as e:
            print(f"Error saving dictionary: {str(e)}")

        return (dictionary,)


class DictLoadFromPath:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "file_path": ("STRING", {"default": ""})
            }
        }

    RETURN_TYPES = ("DICT",)
    FUNCTION = "load_dict_from_path"
    CATEGORY = "dictionary/json"

    def load_dict_from_path(self, file_path):
        try:
            # 파일 경로 확인
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                return ({},)
                
            # JSON 파일 로드
            with open(file_path, 'r', encoding='utf-8') as f:
                loaded_dict = json.load(f)
            print(f"Dictionary loaded from {file_path}")
            
        except Exception as e:
            print(f"Error loading dictionary: {str(e)}")
            loaded_dict = {}

        return (loaded_dict,)
