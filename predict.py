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
ALL_DIRECTORIES = [OUTPUT_DIR, INPUT_DIR, "ComfyUI/temp"]

def main():
    parser = argparse.ArgumentParser(description="Run a ComfyUI workflow.")
    parser.add_argument("--workflow_json", type=str, required=True)
    parser.add_argument("--user_image", type=Path, required=False)
    parser.add_argument("--jersey_image", type=Path, required=False)
    parser.add_argument("--filter_image", type=Path, required=False)
    parser.add_argument("--output_format", type=str, default="webp")
    parser.add_argument("--output_quality", type=int, default=80)
    parser.add_argument("--final_output_path", type=str, default="/app/final_outputs")
    args = parser.parse_args()

    # --- Start Server ---
    server_command = [
        "python3", "/app/ComfyUI/main.py", "--listen", "0.0.0.0", "--cpu",
        "--output-directory", OUTPUT_DIR, "--input-directory", INPUT_DIR, "--disable-metadata"
    ]
    server_process = subprocess.Popen(server_command)
    
    comfyUI = ComfyUI("127.0.0.1:8188")

    try:
        # --- Wait for Server ---
        for i in range(60):
            print(f"Waiting for server, attempt {i+1}...")
            if comfyUI.is_server_running():
                print("Server is ready.")
                break
            time.sleep(1)
        else:
            raise TimeoutError("ComfyUI server failed to start")

        # --- Prepare Environment and Inputs ---
        comfyUI.cleanup(ALL_DIRECTORIES)
        
        # Note: your log shows guy.jpg, workflow expects guy.png. Let's handle this.
        if args.user_image and args.user_image.exists():
            shutil.copy(args.user_image, os.path.join(INPUT_DIR, "guy.png"))
        if args.jersey_image and args.jersey_image.exists():
            shutil.copy(args.jersey_image, os.path.join(INPUT_DIR, "jersey.png"))
        if args.filter_image and args.filter_image.exists():
            shutil.copy(args.filter_image, os.path.join(INPUT_DIR, "filter.png"))

        # --- Load and Run ---
        workflow = json.loads(args.workflow_json)
        wf = comfyUI.load_workflow(workflow)
        comfyUI.connect()
        comfyUI.run_workflow(wf)
        
        # --- Handle Outputs ---
        output_files = comfyUI.get_files([OUTPUT_DIR, "ComfyUI/temp"])
        optimised_files = optimise_images.optimise_image_files(
            args.output_format, args.output_quality, output_files
        )
        final_output_dir = Path(args.final_output_path)
        if not final_output_dir.exists():
            final_output_dir.mkdir(parents=True, exist_ok=True)
        print("--- Copying final outputs ---")
        for file_path in optimised_files:
            if file_path.is_file():
                shutil.copy(file_path, final_output_dir)
                print(f"Copied {file_path.name} to {final_output_dir}")
        print("\nPrediction successful.")

    finally:
        # --- Shutdown ---
        print("Prediction finished. Shutting down ComfyUI server...")
        server_process.terminate()
        server_process.wait()
        print("Server shut down.")

if __name__ == "__main__":
    main()