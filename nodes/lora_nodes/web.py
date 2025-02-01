import os
import json
import hashlib
import folder_paths
from aiohttp import web

# 📌 LoRA 모델이 저장된 기본 폴더 경로를 가져옴
# `folder_paths.get_folder_paths("loras")`는 ComfyUI 내에서 사용되는 경로 검색 함수
LORA_BASE_PATH = folder_paths.get_folder_paths("loras")[0]

# =========================== 📌 1. LoRA 파일 목록 조회 API ===========================
async def list_lora_files(request):
    """
    📌 LoRA 모델 폴더 내부의 서브폴더, .safetensors, .json 파일 목록을 반환하는 API

    반환값:
    {
    "subfolders": ["SD1.5", "SD1.5/Face"],
    "safetensors": ["SD1.5/enhance.safetensor", "SD1.5/Face/eye.safetensor"],
    "jsons": ["SD1.5/enhance_preset.json", "SD1.5/Face/eye_preset.json"]
    }
    """
    subfolders = set()  # 서브폴더 목록을 저장할 set (중복 방지)
    safetensors = []  # .safetensors 파일 목록
    jsons = []  # .json 파일 목록

    # 📌 LORA_BASE_PATH를 기준으로 폴더 탐색
    for root, dirs, files in os.walk(LORA_BASE_PATH):
        rel_root = os.path.relpath(root, LORA_BASE_PATH)  # 기준 폴더로부터 상대경로 계산
        rel_root = rel_root.replace("\\", "/")  # 윈도우 경로 정규화

        if rel_root != ".":  # 현재 폴더(.)가 아니면 서브폴더 목록에 추가
            subfolders.add(rel_root)

        # 📌 현재 폴더에서 파일들을 검사
        for file in files:
            rel_path = os.path.join(rel_root, file).replace("\\", "/")  # 윈도우 경로 정규화

            # 📌 확장자에 따라 파일을 분류
            if file.endswith(".safetensors"):
                safetensors.append(rel_path)
            elif file.endswith(".json"):
                jsons.append(rel_path)

    # 📌 JSON 응답 생성 (경로 정규화된 값 반환)
    response_data = {
        "subfolders": sorted(subfolders),
        "safetensors": sorted(safetensors),
        "jsons": sorted(jsons),
    }
    return web.json_response(response_data)


# =========================== 📌 2. safetensors 파일 해시 계산 API ===========================
async def get_file_hash(request):
    """
    📌 safetensor 파일의 SHA256 해시를 계산하는 API (CivitAI 검색용)

    🔹 Input:
        - HTTP 요청: `GET /lora/hash?path=/SD1.5/enhance.safetensor`
    🔹 Output:
        - JSON 형식으로 파일의 SHA256 해시값 반환
        {
            "hash": "a50376f7d2d6dd9ac329ad35ceffc391bb1cadcaebe53289be65ae5121a823de"
        }
    """

    try:
        file_path = request.query.get("path", "").lstrip("/")  # 요청된 파일 상대경로
        abs_path = os.path.join(LORA_BASE_PATH, file_path)  # 절대경로 변환

        # 📌 파일이 존재하지 않거나 확장자가 safetensors가 아니면 에러 반환
        if not os.path.exists(abs_path) or not abs_path.endswith(".safetensors"):
            return web.json_response({"error": "Invalid file path"}, status=400)

        # 📌 SHA256 해시 계산 (파일을 8192바이트씩 읽으며 해싱)
        hash_sha256 = hashlib.sha256()
        with open(abs_path, "rb") as f:
            while chunk := f.read(8192):
                hash_sha256.update(chunk)

        return web.json_response({"hash": hash_sha256.hexdigest()})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

# =========================== 📌 3. JSON 파일 읽기 API ===========================
async def read_json_file(request):
    """
    📌 JSON 파일을 읽어 내용을 반환하는 API

    🔹 Input:
        - HTTP 요청: `GET /lora/json?path=/SD1.5/enhance_preset.json`
    🔹 Output:
        - JSON 형식으로 파일 내용을 반환
    """

    try:
        file_path = request.query.get("path", "").lstrip("/")  # 요청된 파일 상대경로
        abs_path = os.path.join(LORA_BASE_PATH, file_path)  # 절대경로 변환

        # 📌 파일 존재 여부 및 확장자 확인
        if not os.path.exists(abs_path) or not abs_path.endswith(".json"):
            return web.json_response({"error": "Invalid file path"}, status=400)

        # 📌 JSON 파일 열기 및 내용 읽기
        with open(abs_path, "r", encoding="utf-8") as f:
            data = json.load(f)  # JSON 형식으로 변환

        return web.json_response(data)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

# =========================== 📌 4. JSON 파일 저장 API ===========================
async def save_json_file(request):
    """
    📌 JSON 데이터를 받아 LoRA 폴더 아래에 저장하는 API
    - 요청 형식: {"preset_path": "/SD1.5/custom_preset.json", "data": {...}}
    """
    try:
        request_data = await request.json()  # JSON 데이터 파싱
        preset_path = request_data.get("preset_path", "").lstrip("/")
        json_data = request_data.get("data", {})

        if not preset_path.endswith(".json"):
            return web.json_response({"error": "Invalid preset path (must be .json)"}, status=400)

        abs_path = os.path.join(LORA_BASE_PATH, preset_path)

        # 📌 디렉토리가 없으면 생성
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        # 📌 JSON 파일 저장
        with open(abs_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)

        return web.json_response({
            "message": "Preset saved successfully",
            "path": preset_path
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

# =========================== 📌 5. 서버에 라우트 등록 ===========================
def setup_routes(server):
    """
    📌 LoRA API 엔드포인트 등록

    🔹 등록되는 API:
        - `/lora/list`           -> LoRA 파일 및 폴더 목록 조회
        - `/lora/hash`           -> .safetensors 파일의 SHA256 해시 계산
        - `/lora/json`           -> JSON 파일 내용을 반환
        - `/lora/save_json`        ->JSON 저장
    """

    app = server.app

    # 📌 LoRA 관련 파일 조회 API
    app.router.add_route("GET", "/api/lora/list", list_lora_files)  # LoRA 파일 및 폴더 목록 조회
    app.router.add_route("GET", "/api/lora/hash", get_file_hash)  # safetensors 해시 계산
    app.router.add_route("GET", "/api/lora/json", read_json_file)  # JSON 파일 내용 반환
    app.router.add_route("POST", "/api/lora/save_json", save_json_file)  # Json 저장
