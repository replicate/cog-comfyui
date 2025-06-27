import os
import urllib.request
import subprocess
import threading
import time
import json
import urllib
import uuid
import websocket
import random
import requests
import shutil
import custom_node_helpers as helpers
from pathlib import Path
from node import Node
from weights_downloader import WeightsDownloader
from urllib.error import URLError

# --- ADDED: Define global constants for default directories ---
OUTPUT_DIR = "/tmp/outputs"
INPUT_DIR = "/tmp/inputs"

class ComfyUI:
    def __init__(self, server_address):
        self.weights_downloader = WeightsDownloader()
        self.server_address = server_address
        # --- FIX: Set attributes during initialization ---
        self.input_directory = INPUT_DIR
        self.output_directory = OUTPUT_DIR

    def start_server(self, output_directory, input_directory):
        # This method now also returns the server process
        self.input_directory = input_directory
        self.output_directory = output_directory
        self.apply_helper_methods("prepare", weights_downloader=self.weights_downloader)

        # The server process will be started and managed by this method's caller
        server_process = self.run_server(output_directory, input_directory)

        start_time = time.time()
        while not self.is_server_running():
            if server_process.poll() is not None:
                raise RuntimeError("ComfyUI server process exited unexpectedly.")
            if time.time() - start_time > 60:
                raise TimeoutError("Server did not start within 60 seconds")
            time.sleep(0.5)

        elapsed_time = time.time() - start_time
        print(f"Server started in {elapsed_time:.2f} seconds")
        return server_process

    def run_server(self, output_directory, input_directory):
        # This method is now simplified to just start and return the process
        command = f"python3 ./ComfyUI/main.py --cpu --output-directory {output_directory} --input-directory {input_directory} --disable-metadata"

        print(f"[ComfyUI] Starting server with command: {command}")
        server_process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

        def print_output(pipe, prefix):
            for line in iter(pipe.readline, ""):
                print(f"[{prefix}] {line.strip()}", flush=True)
            pipe.close()

        stdout_thread = threading.Thread(target=print_output, args=(server_process.stdout, "ComfyUI"))
        stderr_thread = threading.Thread(target=print_output, args=(server_process.stderr, "ComfyUI-Error"))
        stdout_thread.start()
        stderr_thread.start()
        
        return server_process

    def is_server_running(self):
        try:
            with urllib.request.urlopen(
                "http://{}/history/{}".format(self.server_address, "123")
            ) as response:
                return response.status == 200
        except URLError:
            return False

    def apply_helper_methods(self, method_name, *args, **kwargs):
        for module_name in dir(helpers):
            module = getattr(helpers, module_name)
            method = getattr(module, method_name, None)
            if callable(method):
                method(*args, **kwargs)

    def handle_weights(self, workflow, weights_to_download=None):
        if weights_to_download is None:
            weights_to_download = []

        print("Checking weights")
        embeddings = self.weights_downloader.get_weights_by_type("EMBEDDINGS")
        embedding_to_fullname = {emb.split(".")[0]: emb for emb in embeddings}
        weights_filetypes = self.weights_downloader.supported_filetypes

        self.convert_lora_loader_nodes(workflow)

        for node in workflow.values():
            if not isinstance(node, dict): continue
            if node.get("class_type") in ["HFHubLoraLoader", "LoraLoaderFromURL"]:
                continue
            self.apply_helper_methods("add_weights", weights_to_download, Node(node))
            if "inputs" in node:
                for input_key, input_value in node["inputs"].items():
                    if isinstance(input_value, str):
                        if any(key in input_value for key in embedding_to_fullname):
                            weights_to_download.extend(
                                embedding_to_fullname[key]
                                for key in embedding_to_fullname
                                if key in input_value
                            )
                        elif any(input_value.endswith(ft) for ft in weights_filetypes):
                            weight_str = self.weights_downloader.get_canonical_weight_str(input_value)
                            if weight_str != input_value:
                                print(f"Converting model synonym {input_value} to {weight_str}")
                                node["inputs"][input_key] = weight_str
                            weights_to_download.append(weight_str)

        weights_to_download = list(set(weights_to_download))
        for weight in weights_to_download:
            self.weights_downloader.download_weights(weight)
        print("====================================")

    def is_image_or_video_value(self, value):
        filetypes = [".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm"]
        return isinstance(value, str) and any(
            value.lower().endswith(ft) for ft in filetypes
        )

    def handle_known_unsupported_nodes(self, workflow):
        for node in workflow.values():
            if isinstance(node, dict):
                self.apply_helper_methods("check_for_unsupported_nodes", Node(node))

    def handle_inputs(self, workflow):
        print("Checking inputs")
        seen_inputs = set()
        missing_inputs = []
        for node in workflow.values():
            if not isinstance(node, dict): continue
            if node.get("class_type") in ["LoraLoaderFromURL", "LoraLoader"]:
                continue
            if "inputs" in node:
                for input_key, input_value in node["inputs"].items():
                    if isinstance(input_value, str) and input_value not in seen_inputs:
                        seen_inputs.add(input_value)
                        if input_value.startswith(("http://", "https://")):
                            filename = os.path.join(
                                self.input_directory, os.path.basename(input_value)
                            )
                            if not os.path.exists(filename):
                                print(f"Downloading {input_value} to {filename}")
                                try:
                                    response = requests.get(input_value)
                                    response.raise_for_status()
                                    with open(filename, "wb") as file:
                                        file.write(response.content)
                                    print(f"✅ {filename}")
                                except requests.exceptions.RequestException as e:
                                    print(f"❌ Error downloading {input_value}: {e}")
                                    missing_inputs.append(filename)
                            node["inputs"][input_key] = os.path.basename(filename)
                        elif self.is_image_or_video_value(input_value):
                            filename = os.path.join(
                                self.input_directory, os.path.basename(input_value)
                            )
                            if not os.path.exists(filename):
                                print(f"❌ {filename} not provided")
                                missing_inputs.append(filename)
                            else:
                                print(f"✅ {filename}")

        if missing_inputs:
            raise Exception(f"Missing required input files: {', '.join(missing_inputs)}")

    def connect(self):
        self.client_id = str(uuid.uuid4())
        self.ws = websocket.WebSocket()
        self.ws.connect(f"ws://{self.server_address}/ws?clientId={self.client_id}")

    def post_request(self, endpoint, data=None):
        url = f"http://{self.server_address}{endpoint}"
        headers = {"Content-Type": "application/json"} if data else {}
        json_data = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(url, data=json_data, headers=headers, method="POST")
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                print(f"Failed: {endpoint}, status code: {response.status}")

    def clear_queue(self):
        self.post_request("/queue", {"clear": True})
        self.post_request("/interrupt")

    def queue_prompt(self, prompt):
        try:
            p = {"prompt": prompt, "client_id": self.client_id}
            data = json.dumps(p).encode("utf-8")
            req = urllib.request.Request(f"http://{self.server_address}/prompt", data=data)
            output = json.loads(urllib.request.urlopen(req).read())
            return output["prompt_id"]
        except urllib.error.HTTPError as e:
            print(f"ComfyUI error: {e.code} {e.reason} {e.read().decode('utf-8')}")
            raise Exception("ComfyUI Error – Your workflow could not be run.")

    def _delete_corrupted_weights(self, error_data):
        if "current_inputs" in error_data:
            weights_to_delete = []
            weights_filetypes = self.weights_downloader.supported_filetypes
            for input_list in error_data["current_inputs"].values():
                for input_value in input_list:
                    if isinstance(input_value, str) and any(input_value.endswith(ft) for ft in weights_filetypes):
                        weights_to_delete.append(input_value)
            for weight_file in list(set(weights_to_delete)):
                self.weights_downloader.delete_weights(weight_file)
            raise Exception("Corrupted weights deleted. Please try again.")

    def wait_for_prompt_completion(self, workflow, prompt_id):
        while True:
            out = self.ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message["type"] == "execution_error":
                    error_data = message["data"]
                    if "exception_type" in error_data and error_data["exception_type"] == "safetensors_rust.SafetensorError":
                        self._delete_corrupted_weights(error_data)
                    if "exception_message" in error_data and "Unauthorized" in error_data["exception_message"]:
                        raise Exception("ComfyUI API nodes are not currently supported.")
                    error_message = json.dumps(message, indent=2)
                    raise Exception(f"Workflow execution error:\n\n{error_message}")
                if message["type"] == "executing":
                    data = message["data"]
                    if data["node"] is None and data["prompt_id"] == prompt_id:
                        break
                    elif data["prompt_id"] == prompt_id:
                        node = workflow.get(data["node"], {})
                        meta = node.get("_meta", {})
                        class_type = node.get("class_type", "Unknown")
                        print(f"Executing node {data['node']}, title: {meta.get('title', 'Unknown')}, class type: {class_type}")
            else:
                continue

    def load_workflow(self, workflow):
        if not isinstance(workflow, dict):
            wf = json.loads(workflow)
        else:
            wf = workflow
        if any(key in wf.keys() for key in ["last_node_id", "last_link_id", "version"]):
            raise ValueError("You must use the API JSON version of a ComfyUI workflow.")
        self.handle_known_unsupported_nodes(wf)
        self.handle_inputs(wf)
        self.handle_weights(wf)
        return wf

    def run_workflow(self, workflow):
        print("Running workflow")
        prompt_id = self.queue_prompt(workflow)
        self.wait_for_prompt_completion(workflow, prompt_id)
        output_json = self.get_history(prompt_id)
        print("outputs: ", output_json)
        print("====================================")

    def get_history(self, prompt_id):
        with urllib.request.urlopen(f"http://{self.server_address}/history/{prompt_id}") as response:
            output = json.loads(response.read())
            return output[prompt_id]["outputs"]

    def get_files(self, directories, prefix="", file_extensions=None):
        files = []
        if isinstance(directories, str):
            directories = [directories]
        for directory in directories:
            if not os.path.exists(directory):
                print(f"Warning: Directory {directory} does not exist. Skipping.")
                continue
            for f in os.listdir(directory):
                if f == "__MACOSX":
                    continue
                path = os.path.join(directory, f)
                if os.path.isfile(path):
                    files.append(Path(path))
                elif os.path.isdir(path):
                    files.extend(self.get_files(path, prefix=f"{prefix}{f}/"))
        if file_extensions:
            files = [f for f in files if f.name.split(".")[-1] in file_extensions]
        return sorted(files)

    def cleanup(self, directories):
        self.clear_queue()
        for directory in directories:
            if os.path.exists(directory):
                shutil.rmtree(directory)
            os.makedirs(directory)

    def convert_lora_loader_nodes(self, workflow):
        for node in workflow.values():
            if isinstance(node, dict) and node.get("class_type") == "LoraLoader":
                inputs = node.get("inputs", {})
                if "lora_name" in inputs and isinstance(inputs["lora_name"], str):
                    if inputs["lora_name"].startswith(("http://", "https://")):
                        print("Converting LoraLoader node to LoraLoaderFromURL")
                        node["class_type"] = "LoraLoaderFromURL"
                        node["inputs"]["url"] = inputs["lora_name"]
                        del node["inputs"]["lora_name"]