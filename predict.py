# predict.py (Final, Corrected Version)

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
    # ... (all your argparse arguments)
    parser.add_argument("--workflow_json", type=str, required=True)
    parser.add_argument("--user_image", type=Path, required=False)
    parser.add_argument("--jersey_image", type=Path, required=False)
    parser.add_argument("--filter_image", type=Path, required=False)
    parser.add_argument("--output_format", type=str, default="webp")
    parser.add_argument("--output_quality", type=int, default=80)
    parser.add_argument("--final_output_path", type=str, default="/app/final_outputs")
    args = parser.parse_args()

    # --- 2. Initialize ComfyUI Client ---
    comfyUI = ComfyUI("127.0.0.1:8188")
    
    # --- 3. Start Server and Prepare Environment ---
    # This call is crucial. It does two things:
    #   a) Sets self.input_directory and self.output_directory
    #   b) Starts the server process in the background.
    comfyUI.start_server(OUTPUT_DIR, INPUT_DIR)

    # --- 4. Main Application Logic inside a try...finally block ---
    try:
        # Prepare Inputs by copying them to the directory ComfyUI is watching.
        # This can now happen after the server starts.
        if args.user_image and args.user_image.exists():
            shutil.copy(args.user_image, os.path.join(INPUT_DIR, "guy.png"))
        if args.jersey_image and args.jersey_image.exists():
            shutil.copy(args.jersey_image, os.path.join(INPUT_DIR, "jersey.png"))
        if args.filter_image and args.filter_image.exists():
            shutil.copy(args.filter_image, os.path.join(INPUT_DIR, "filter.png"))
        
        print("====================================")
        print(f"Inputs prepared in {INPUT_DIR}:")
        for f in os.listdir(INPUT_DIR):
            print(f"- {f}")
        print("====================================")

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
        # The comfyui.py start_server method doesn't return the process object,
        # so we can't kill it directly here. The container exiting will handle this.
        # This is less clean, but works with the current comfyui.py structure.
        print("Prediction process finished. Container will now exit, stopping the server.")


if __name__ == "__main__":
    main()