# lbbw-trikot-main/predict_docker.py

import os
import json
import shutil
import argparse
import sys
from pathlib import Path
from comfyui import ComfyUI
from cog_model_helpers import optimise_images

# Define directories
OUTPUT_DIR = "/tmp/outputs"
INPUT_DIR = "/tmp/inputs"
COMFYUI_TEMP_OUTPUT_DIR = "ComfyUI/temp"
ALL_DIRECTORIES = [OUTPUT_DIR, INPUT_DIR, COMFYUI_TEMP_OUTPUT_DIR]

def main():
    parser = argparse.ArgumentParser(description="Run a ComfyUI workflow from the command line.")
    parser.add_argument(
        "--workflow_json",
        type=str,
        required=True,
        help="The ComfyUI API workflow as a JSON string.",
    )
    parser.add_argument(
        "--output_format",
        type=str,
        default="webp",
        help="Format for the output images (e.g., webp, jpg, png).",
    )
    parser.add_argument(
        "--output_quality",
        type=int,
        default=80,
        help="Quality for the output images (0-100).",
    )
    parser.add_argument(
        "--final_output_path",
        type=str,
        default="/app/final_outputs",
        help="The directory inside the container where final images will be saved.",
    )
    args = parser.parse_args()

    comfyUI = ComfyUI("127.0.0.1:8188")
    
    comfyUI.cleanup(ALL_DIRECTORIES)

    try:
        workflow = json.loads(args.workflow_json)
    except json.JSONDecodeError:
        print("Error: Invalid JSON in workflow_json argument.")
        sys.exit(1)
        
    comfyUI.handle_weights(workflow) # Still need this to identify weights from the workflow, even if not downloading.
    comfyUI.handle_inputs(workflow)

    comfyUI.connect()
    comfyUI.run_workflow(workflow)

    output_files = comfyUI.get_files([OUTPUT_DIR])
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
        else:
            print(f"Skipping directory {file_path}")


if __name__ == "__main__":
    main()