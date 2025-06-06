import json
import urllib.request
import time
import subprocess
import os
try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    try:
        from websocket import WebSocket
        WEBSOCKET_AVAILABLE = True
    except ImportError:
        WEBSOCKET_AVAILABLE = False
        print("Warning: websocket module not available, using alternative connection method")

import threading
import sys
import base64
import requests
import psutil

def start_comfyui(comfyui_path):
    try:
        # Try to find the correct comfy command
        import shutil
        if shutil.which('comfy'):
            comfy_cmd = 'comfy'
        else:
            comfy_cmd = 'python -m comfy_cli'
        
        process = subprocess.Popen(f"{comfy_cmd} --skip-prompt --workspace={comfyui_path} launch -- --listen 127.0.0.1 --port 8188", shell=True)
        # Wait for a short time to see if the process starts successfully
        time.sleep(5)
        
        if process.poll() is None:
            return process
        else:
            stdout, stderr = process.communicate()
            raise Exception("ComfyUI server failed to start")
    except Exception as e:
        raise Exception("Error setting up ComfyUI repo") from e

def run_comfyui_in_background(comfyui_path):
    def run_server():
        process = start_comfyui(comfyui_path)
        if process:
            stdout, stderr = process.communicate()

    server_thread = threading.Thread(target=run_server)
    server_thread.start()

def check_comfyui(server_address, client_id):
    if not WEBSOCKET_AVAILABLE:
        # Use HTTP polling as fallback
        max_retries = 60
        for i in range(max_retries):
            try:
                response = requests.get(f"http://{server_address}/", timeout=5)
                if response.status_code == 200:
                    return None  # Return None to indicate HTTP mode
            except:
                pass
            time.sleep(5)
        raise Exception("ComfyUI server not available")
    
    socket_connected = False
    ws = None
    while not socket_connected:
        try:
            if hasattr(websocket, 'WebSocket'):
                ws = websocket.WebSocket()
            else:
                ws = websocket.create_connection(f"ws://{server_address}/ws?clientId={client_id}")
                return ws
            ws.connect(f"ws://{server_address}/ws?clientId={client_id}")
            socket_connected = True
        except Exception as e:
            time.sleep(5)
    return ws

def load_workflow(workflow_path):
    with open(f"{workflow_path}", 'rb') as file:
        return json.load(file)

def prompt_update_workflow(workflow,prompt,negative_prompt=None):
    workflow["6"]["inputs"]["text"] = prompt
    if negative_prompt:
        workflow["7"]["inputs"]["text"]  = negative_prompt
        
    return workflow
    
def send_comfyui_request(ws, prompt, server_address, client_id):
    p = {"prompt": prompt,"client_id": client_id}
    data = json.dumps(p).encode("utf-8")
    url = f"http://{server_address}/prompt"
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

    with urllib.request.urlopen(req, timeout=10) as response:
        response = json.loads(response.read())
    
    prompt_id = response["prompt_id"]
    
    if ws is None or not WEBSOCKET_AVAILABLE:
        # Use HTTP polling instead of websocket
        return wait_for_completion_http(server_address, prompt_id)
    
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message["type"] == "executing":
                data = message["data"]
                if data["node"] is None and data["prompt_id"] == prompt_id:
                    break
        else:
            continue
    return prompt_id

def wait_for_completion_http(server_address, prompt_id):
    """Fallback method using HTTP polling instead of websocket"""
    max_attempts = 120  # 10 minutes with 5 second intervals
    for _ in range(max_attempts):
        try:
            with urllib.request.urlopen(f"http://{server_address}/history/{prompt_id}", timeout=10) as response:
                history = json.loads(response.read())
                if prompt_id in history:
                    return prompt_id
        except:
            pass
        time.sleep(5)
    raise Exception("Timeout waiting for completion")

def get_img_file_path(server_address,prompt_id):
    with urllib.request.urlopen(
        "http://{}/history/{}".format(server_address, prompt_id),timeout=10
    ) as response:
        output = json.loads(response.read())
    outputs = output[prompt_id]["outputs"]
    for node_id in outputs:
        node_output = outputs[node_id]
      
    if "images" in node_output:
        image_outputs = []
        for image in node_output["images"]:
                image_outputs.append({"filename": image.get("filename")})
    
    for node_id in image_outputs:
        file_path = f"/output/{node_id.get('filename')}"
    
    return file_path

def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        return encoded_string.decode('utf-8')
        
def stop_server_on_port(port):
    for connection in psutil.net_connections():
        if connection.laddr.port == port:
            process = psutil.Process(connection.pid)
            process.terminate()

def is_comfyui_running(server_address="127.0.0.1:8188"):
    try:
        response = requests.get(f"http://{server_address}/", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False
