# predict.py (Final Corrected Version)

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

# Define directories
OUTPUT_DIR = "/tmp/outputs"
INPUT_DIR = "/tmp/inputs"
ALL_DIRECTORIES = [OUTPUT_DIR, INPUT_DIR, "ComfyUI/temp"]

def main():
    # --- 1. Parse Arguments ---
    parser = argparse.ArgumentParser(description="Run a ComfyUI workflow.")
    parser.add_argument("--workflow_json_file", type=Path, required=True)
    parser.add_argument("--user_image", type=Path, required=False)
    parser.add_argument("--jersey_image", type=Path, required=False)
    parser.add_argument("--filter_image", type=Path, required=False)
    parser.add_argument("--final_output_path", type=str, required=True)
    # Add back other args if you need them, e.g., output_format, output_quality
    args = parser.parse_args()

    # --- 2. Start ComfyUI Server in the background ---
    server_command = [
        "python3", "/app/ComfyUI/main.py", "--listen", "0.0.0.0", "--cpu",
        "--output-directory", OUTPUT_DIR, "--input-directory", INPUT_DIR
    ]
    print("Starting ComfyUI server...")
    server_process = subprocess.Popen(server_command)
    print(f"ComfyUI server started with PID: {server_process.pid}")
    
    comfyUI = ComfyUI("127.0.0.1:8188")

    try:
        # --- 3. Wait for Server to be ready ---
        for i in range(60):
            if comfyUI.is_server_running():
                print("Server is ready.")
                break
            time.sleep(1)
        else: # This else belongs to the for loop, it runs if the loop finishes without `break`
            raise TimeoutError("ComfyUI server did not start in 60 seconds")

        # --- 4. Prepare Environment and Inputs ---
        # THIS IS THE CRITICAL FIX: Create the directories *before* trying to copy into them.
        comfyUI.cleanup(ALL_DIRECTORIES)

        # Now copy the files from their mounted location to the INPUT_DIR that ComfyUI watches.
        # Your log shows you provide guy.jpg but the workflow expects guy.png. We'll handle this.
        if args.user_image and args.user_image.exists():
            shutil.copy(args.user_image, os.path.join(INPUT_DIR, "guy.png"))
        if args.jersey_image and args.jersey_image.exists():
            shutil.copy(args.jersey_image, os.path.join(INPUT_DIR, "jersey.png"))
        if args.filter_image and args.filter_image.exists():
            shutil.copy(args.filter_image, os.path.join(INPUT_DIR, "filter.png"))

        # --- 5. Load and Run Workflow ---
        with open(args.workflow_json_file, 'r') as f:
            workflow_data = json.load(f)
            
        wf = comfyUI.load_workflow(workflow_data)
        comfyUI.connect()
        comfyUI.run_workflow(wf)

        # --- 6. Handle Outputs ---
        output_files = comfyUI.get_files([OUTPUT_DIR, "ComfyUI/temp"])
        # We'll just copy, not optimize for now to keep it simple.
        # optimised_files = optimise_images.optimise_image_files(...) 

        final_output_dir = Path(args.final_output_path)
        final_output_dir.mkdir(parents=True, exist_ok=True)
        print("--- Copying final outputs ---")
        for file_path in output_files:
            if file_path.is_file():
                shutil.copy(file_path, final_output_dir)
                print(f"Copied {file_path.name} to {final_output_dir}")
        print("\nPrediction successful.")

    finally:
        # --- 7. Ensure Server is Always Shut Down ---
        if server_process:
            print("Prediction process finished. Shutting down ComfyUI server...")
            server_process.terminate()
            server_process.wait()
            print("Server shut down.")

if __name__ == "__main__":
    main()