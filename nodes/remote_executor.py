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


import sqlite3
import numpy as np
import torch
import pickle
import io
import json

class DatabaseNode:
    def __init__(self):
        self.db_path = "comfy_storage.db"
        self.init_db()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "operation": (["save", "load"],),
                "key": ("STRING", {"default": ""}),
            },
            "optional": {
                "image": ("IMAGE",),
                "mask": ("MASK",),
                "dictionary": ("DICT",),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "DICT")
    FUNCTION = "process"
    CATEGORY = "database"

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS stored_data
                    (key TEXT PRIMARY KEY, image BLOB, mask BLOB, dictionary TEXT)''')
        conn.commit()
        conn.close()

    def save_data(self, key, image=None, mask=None, dictionary=None):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Serialize tensors directly
        image_bytes = pickle.dumps(image) if image is not None else None
        mask_bytes = pickle.dumps(mask) if mask is not None else None
        dict_str = json.dumps(dictionary) if dictionary else None

        c.execute('INSERT OR REPLACE INTO stored_data VALUES (?, ?, ?, ?)',
                  (key, image_bytes, mask_bytes, dict_str))
        conn.commit()
        conn.close()

    def load_data(self, key):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT * FROM stored_data WHERE key = ?', (key,))
        row = c.fetchone()
        conn.close()

        if not row:
            return None, None, None

        # Deserialize tensors directly
        image = pickle.loads(row[1]) if row[1] else None
        mask = pickle.loads(row[2]) if row[2] else None
        dictionary = json.loads(row[3]) if row[3] else {}

        return image, mask, dictionary

    def process(self, operation, key, image=None, mask=None, dictionary=None):
        if operation == "save":
            self.save_data(key, image, mask, dictionary)
            return (image if image is not None else torch.zeros(1),
                    mask if mask is not None else torch.zeros(1),
                    dictionary if dictionary is not None else {})
        else:
            return self.load_data(key)


import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import requests
import time


class GateServer(BaseHTTPRequestHandler):
    received_signal = False

    def do_POST(self):
        self.__class__.received_signal = True
        self.send_response(200)
        self.end_headers()


class GateServerNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "data": ("DICT",),
                "port": ("INT", {"default": 8188, "min": 1024, "max": 65535}),
                "timeout": ("FLOAT", {"default": 300.0, "min": 0.1}),
            }
        }

    RETURN_TYPES = ("DICT",)
    FUNCTION = "run_server"
    CATEGORY = "flow_control"

    def run_server(self, data, port, timeout):
        GateServer.received_signal = False
        server = HTTPServer(('localhost', port), GateServer)
        server.timeout = timeout

        def serve():
            while not GateServer.received_signal:
                server.handle_request()

        thread = threading.Thread(target=serve)
        thread.start()
        thread.join(timeout)

        server.server_close()

        if not GateServer.received_signal:
            raise TimeoutError(f"Gate server timed out after {timeout} seconds")

        return (data,)


class GateClientNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "data": ("DICT",),
                "server_url": ("STRING", {"default": "http://localhost:8188"}),
            }
        }

    RETURN_TYPES = tuple()
    OUTPUT_NODE = True
    FUNCTION = "signal_server"
    CATEGORY = "flow_control"

    def signal_server(self, data, server_url):
        try:
            response = requests.post(server_url, json={"signal": True})
            response.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"Failed to signal gate server: {str(e)}")
        return tuple()
