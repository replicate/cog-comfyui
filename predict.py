import os
import shutil
import json
import argparse
import sys
import subprocess
import time
from pathlib import Path
from comfyui import ComfyUI
from cog_model_helpers import optimise_images

OUTPUT_DIR = "/tmp/outputs"
INPUT_DIR = "/tmp/inputs"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow_json_file", type=Path, required=True)
    parser.add_argument("--user_image", type=Path, required=True)
    parser.add_argument("--jersey_image", type=Path, required=True)
    parser.add_argument("--filter_image", type=Path, required=True)
    parser.add_argument("--final_output_path", type=str, required=True)
    args = parser.parse_args()

    # Start Server
    server_command = [
        "python3", "/app/ComfyUI/main.py", "--listen", "0.0.0.0", "--cpu",
        "--output-directory", OUTPUT_DIR, "--input-directory", INPUT_DIR
    ]
    server_process = subprocess.Popen(server_command)
    
    comfyUI = ComfyUI("127.0.0.1:8188")
    
    try:
        # Wait for server
        for _ in range(60):
            if comfyUI.is_server_running():
                print("Server is ready.")
                break
            time.sleep(1)
        else:
            raise TimeoutError("Server did not start")

        # Prepare environment and inputs
        comfyUI.cleanup([OUTPUT_DIR, INPUT_DIR, "ComfyUI/temp"])
        shutil.copy(args.user_image, os.path.join(INPUT_DIR, "guy.png"))
        shutil.copy(args.jersey_image, os.path.join(INPUT_DIR, "jersey.png"))
        shutil.copy(args.filter_image, os.path.join(INPUT_DIR, "filter.png"))

        # Load and run workflow
        with open(args.workflow_json_file, 'r') as f:
            workflow_data = json.load(f)
            
        wf = comfyUI.load_workflow(workflow_data)
        comfyUI.connect()
        comfyUI.run_workflow(wf)

        # Handle outputs
        output_files = comfyUI.get_files([OUTPUT_DIR, "ComfyUI/temp"])
        final_output_dir = Path(args.final_output_path)
        final_output_dir.mkdir(parents=True, exist_ok=True)
        for file_path in output_files:
            shutil.copy(file_path, final_output_dir)

        print("--- Verification: Files in final output directory ---")
        for f in os.listdir(final_output_dir):
            print(f"- {f}")
            
    finally:
        server_process.terminate()
        server_process.wait()
        print("Server shut down.")

if __name__ == "__main__":
    main()