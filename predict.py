# predict.py (Updated for new workflow)

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
    # --- 1. Parse Arguments ---
    parser = argparse.ArgumentParser(description="Run a ComfyUI workflow.")
    parser.add_argument("--workflow_json_file", type=Path, required=True)
    
    # Add arguments for ALL possible image inputs
    parser.add_argument("--user_image", type=Path, required=False)
    parser.add_argument("--jersey_image", type=Path, required=False)
    parser.add_argument("--filter_image", type=Path, required=False)
    # --- NEW: Add location_image argument ---
    parser.add_argument("--location_image", type=Path, required=False)
    
    parser.add_argument("--final_output_path", type=str, required=True)
    # Add other args like output_format, etc. if you need to control them
    args = parser.parse_args()

    # --- 2. Start Server ---
    server_command = [
        "python3", "/app/ComfyUI/main.py", "--listen", "0.0.0.0", "--cpu",
        "--output-directory", OUTPUT_DIR, "--input-directory", INPUT_DIR
    ]
    server_process = subprocess.Popen(server_command)
    comfyUI = ComfyUI("127.0.0.1:8188")
    
    try:
        # --- 3. Wait for Server ---
        for _ in range(60):
            if comfyUI.is_server_running():
                print("Server is ready.")
                break
            time.sleep(1)
        else:
            raise TimeoutError("Server did not start")

        # --- 4. Prepare Environment and Inputs ---
        comfyUI.cleanup(ALL_DIRECTORIES)

        # Copy all provided files to the INPUT_DIR that ComfyUI watches.
        # The destination filenames MUST match what's in the workflow JSON.
        if args.user_image and args.user_image.exists():
            shutil.copy(args.user_image, os.path.join(INPUT_DIR, "guy.png"))
        if args.jersey_image and args.jersey_image.exists():
            shutil.copy(args.jersey_image, os.path.join(INPUT_DIR, "jersey.png"))
        if args.filter_image and args.filter_image.exists():
            shutil.copy(args.filter_image, os.path.join(INPUT_DIR, "filter.png"))
        # --- NEW: Copy location_image ---
        if args.location_image and args.location_image.exists():
            shutil.copy(args.location_image, os.path.join(INPUT_DIR, "location.png"))

        # --- 5. Load and Run Workflow ---
        with open(args.workflow_json_file, 'r') as f:
            workflow_data = json.load(f)
            
        wf = comfyUI.load_workflow(workflow_data)
        comfyUI.connect()
        comfyUI.run_workflow(wf)

        # --- 6. Handle and Verify Outputs ---
        output_files = comfyUI.get_files([OUTPUT_DIR, "ComfyUI/temp"])
        final_output_dir = Path(args.final_output_path)
        final_output_dir.mkdir(parents=True, exist_ok=True)
        
        print("--- Copying final outputs ---")
        for file_path in output_files:
            if file_path.is_file():
                shutil.copy(file_path, final_output_dir)
                print(f"Copied {file_path.name} to {final_output_dir}")

        print("\n--- Verifying final outputs on volume ---")
        final_files = os.listdir(args.final_output_path)
        if final_files:
            print(f"Successfully found {len(final_files)} file(s) in {args.final_output_path}:")
            for f in final_files:
                print(f"- {f}")
        else:
            print(f"Warning: Final output directory {args.final_output_path} is empty.")
            
        print("\nPrediction successful.")

    finally:
        # --- 7. Shutdown ---
        if server_process:
            print("Prediction process finished. Shutting down ComfyUI server...")
            server_process.terminate()
            server_process.wait()
            print("Server shut down.")

if __name__ == "__main__":
    main()