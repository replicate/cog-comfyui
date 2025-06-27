# predict.py (All-in-One Version)

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

# Define directories used by ComfyUI
OUTPUT_DIR = "/tmp/outputs"
INPUT_DIR = "/tmp/inputs"
ALL_DIRECTORIES = [OUTPUT_DIR, INPUT_DIR, "ComfyUI/temp"]

def main():
    # --- 1. Parse Command-Line Arguments ---
    parser = argparse.ArgumentParser(description="Run a ComfyUI workflow from the command line.")
    parser.add_argument("--workflow_json", type=str, required=True)
    parser.add_argument("--user_image", type=Path, required=True)
    parser.add_argument("--jersey_image", type=Path, required=True)
    parser.add_argument("--filter_image", type=Path, required=True)
    parser.add_argument("--output_format", type=str, default="webp")
    parser.add_argument("--output_quality", type=int, default=80)
    parser.add_argument("--final_output_path", type=str, default="/app/final_outputs")
    args = parser.parse_args()

    # --- 2. Start ComfyUI Server in the Background ---
    server_command = [
        "python3",
        "/app/ComfyUI/main.py",
        "--listen", "0.0.0.0",
        "--cpu",
        "--output-directory", OUTPUT_DIR,
        "--input-directory", INPUT_DIR,
        "--disable-metadata"
    ]
    
    print("Starting ComfyUI server...")
    # Use Popen to run the server as a background process
    server_process = subprocess.Popen(server_command)
    print(f"ComfyUI server started with PID: {server_process.pid}")

    # --- 3. Wait for Server to be Ready ---
    comfyUI = ComfyUI("127.0.0.1:8188")
    is_ready = False
    max_retries = 60
    for i in range(max_retries):
        print(f"Waiting for server, attempt {i+1}/{max_retries}...")
        if comfyUI.is_server_running():
            is_ready = True
            print("ComfyUI server is ready.")
            break
        time.sleep(1)
    
    if not is_ready:
        print("Error: ComfyUI server failed to start.")
        server_process.terminate() # Try to clean up
        server_process.wait()
        sys.exit(1)

    # --- 4. Main Application Logic ---
    try:
        # Clean directories (after server is up, to be safe)
        comfyUI.cleanup(ALL_DIRECTORIES)

        # Prepare Inputs
        shutil.copy(args.user_image, os.path.join(INPUT_DIR, "guy.jpg"))
        shutil.copy(args.jersey_image, os.path.join(INPUT_DIR, "jersey.png"))
        shutil.copy(args.filter_image, os.path.join(INPUT_DIR, "filter.png"))

        # Load and Run Workflow
        workflow = json.loads(args.workflow_json)
        wf = comfyUI.load_workflow(workflow)
        comfyUI.connect()
        comfyUI.run_workflow(wf)

        # Handle Outputs
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
        # --- 5. Ensure Server is Shut Down ---
        print("Prediction finished. Shutting down ComfyUI server...")
        server_process.terminate()
        server_process.wait()
        print("Server shut down.")


if __name__ == "__main__":
    main()