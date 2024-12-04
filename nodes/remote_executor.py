import asyncio
import websockets
import json
import requests
import time
import io
import traceback
import random
import numpy as np
import torch
from PIL import Image, ImageOps, ImageSequence, ImageFile
class RemoteWorkflowExecutor:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "remote_host": ("STRING", {"default": "127.0.0.1"}),
                "remote_port": ("INT", {"default": 8188, "min": 1, "max": 65535}),
                "default_image": ("IMAGE",),
                "timeout": ("INT", {"default": 300, "min": 1}),
                "front_of_queue": ("BOOLEAN", {"default": False})
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "execute_remote"
    CATEGORY = "remote"

    def execute_remote(self, remote_host, remote_port, default_image, timeout, front_of_queue=False):
        try:
            remote_url = f"http://{remote_host}:{remote_port}"
            test_response = requests.get(f"{remote_url}/history")
            history = test_response.json()
            latest_prompt_id = next(iter(history))
            workflow = history[latest_prompt_id]["prompt"][2]

            workflow['38']['inputs']['seed'] = random.randint(1, 1000000000)

            response = requests.post(f"{remote_url}/prompt", json={
                "prompt": workflow,
                "front": front_of_queue,
                "client_id": "comfyui_node"
            })
            prompt_id = response.json()["prompt_id"]

            start_time = time.time()
            while time.time() - start_time < timeout:
                history = requests.get(f"{remote_url}/history/{prompt_id}").json()
                if prompt_id not in history:
                    time.sleep(0.5)
                    continue

                status = history[prompt_id].get("status", {})
                if status.get("completed"):
                    outputs = history[prompt_id].get("outputs", {})
                    for node_output in outputs.values():
                        if "images" in node_output:
                            image_data = node_output["images"][0]
                            image_url = f"{remote_url}/view?filename={image_data['filename']}&type={image_data['type']}&subfolder={image_data.get('subfolder', '')}"
                            response = requests.get(image_url)
                            if response.ok:
                                i = Image.open(io.BytesIO(response.content))
                                i = ImageOps.exif_transpose(i)
                                if i.mode == 'I':
                                    i = i.point(lambda i: i * (1 / 255))
                                image = i.convert("RGB")
                                image = np.array(image).astype(np.float32) / 255.0
                                image = torch.from_numpy(image)[None,]
                                return (image,)

                elif "error" in status.get("status_str", ""):
                    return (default_image,)
                time.sleep(0.5)
            return (default_image,)

        except Exception as e:
            print(f"[ERROR] Exception: {str(e)}\n{traceback.format_exc()}")
            return (default_image,)