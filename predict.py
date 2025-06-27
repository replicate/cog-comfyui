# predict.py (Final Corrected Version)

import os
import shutil
import json
import argparse
import sys
import time
from pathlib import Path
from comfyui import ComfyUI
from cog_model_helpers import optimise_images

OUTPUT_DIR = "/tmp/outputs"
INPUT_DIR = "/tmp/inputs"

def main():
    parser = argparse.ArgumentParser(description="Run a ComfyUI workflow.")
    parser.add_argument("--workflow_json_file", type=Path, required=True)
    parser.add_argument("--user_image", type=Path, required=False)
    parser.add_argument("--jersey_image", type=Path, required=False)
    parser.add_argument("--filter_image", type=Path, required=False)
    parser.add_argument("--final_output_path", type=str, required=True)
    args = parser.parse_args()

    comfyUI = ComfyUI("127.0.0.1:8188")
    server_process = None  # Initialize to None

    try:
        # --- Start Server ---
        # This now returns the process object we need to manage
        server_process = comfyUI.start_server(OUTPUT_DIR, INPUT_DIR)

        # --- Prepare Inputs ---
        # This now happens AFTER the server (and directories) are set up.
        if args.user_image and args.user_image.exists():
            shutil.copy(args.user_image, os.path.join(INPUT_DIR, "guy.png"))
        if args.jersey_image and args.jersey_image.exists():
            shutil.copy(args.jersey_image, os.path.join(INPUT_DIR, "jersey.png"))
        if args.filter_image and args.filter_image.exists():
            shutil.copy(args.filter_image, os.path.join(INPUT_DIR, "filter.png"))

        # --- Load and Run Workflow ---
        with open(args.workflow_json_file, 'r') as f:
            workflow_data = json.load(f)
            
        # load_workflow will now succeed because start_server has set the necessary attributes
        wf = comfyUI.load_workflow(workflow_data)
        comfyUI.connect()
        comfyUI.run_workflow(wf)

        # --- Handle Outputs ---
        output_files = comfyUI.get_files([OUTPUT_DIR, "ComfyUI/temp"])
        # This is a placeholder for your actual optimisation function
        # optimised_files = optimise_images.optimise_image_files(args.output_format, args.output_quality, output_files)

        final_output_dir = Path(args.final_output_path)
        final_output_dir.mkdir(parents=True, exist_ok=True)
        print("--- Copying final outputs ---")
        for file_path in output_files: # Use output_files directly
            if file_path.is_file():
                shutil.copy(file_path, final_output_dir)
                print(f"Copied {file_path.name} to {final_output_dir}")
        print("\nPrediction successful.")

    finally:
        # --- Shutdown ---
        if server_process:
            print("Prediction process finished. Shutting down ComfyUI server...")
            server_process.terminate()
            server_process.wait()
            print("Server shut down.")

if __name__ == "__main__":
    main()