# predict.py (Final, Corrected Docker Version)

import os
import shutil
import json
import argparse
import sys
from pathlib import Path
from comfyui import ComfyUI
from cog_model_helpers import optimise_images

# Define directories used by ComfyUI
OUTPUT_DIR = "/tmp/outputs"
INPUT_DIR = "/tmp/inputs" # This is where ComfyUI looks for files
ALL_DIRECTORIES = [OUTPUT_DIR, INPUT_DIR, "ComfyUI/temp"]

def main():
    # --- 1. Parse Command-Line Arguments ---
    parser = argparse.ArgumentParser(description="Run a ComfyUI workflow from the command line.")
    parser.add_argument("--workflow_json", type=str, required=True, help="The ComfyUI API workflow as a JSON string.")
    
    # These paths are where the files are mounted INSIDE the container
    parser.add_argument("--user_image", type=Path, required=True, help="Path to the user's image inside the container.")
    parser.add_argument("--jersey_image", type=Path, required=True, help="Path to the jersey image inside the container.")
    parser.add_argument("--filter_image", type=Path, required=True, help="Path to the fallback/filter image inside the container.")
    
    parser.add_argument("--output_format", type=str, default="webp")
    parser.add_argument("--output_quality", type=int, default=80)
    parser.add_argument("--final_output_path", type=str, default="/app/final_outputs")
    args = parser.parse_args()

    # --- 2. Set up ComfyUI Environment ---
    comfyUI = ComfyUI("127.0.0.1:8188")
    # This just cleans the directories, it doesn't start the server yet.
    comfyUI.cleanup(ALL_DIRECTORIES)

    # --- 3. Prepare Inputs (CRUCIAL STEP) ---
    # We copy the files from their mounted location to the INPUT_DIR that ComfyUI is configured to use.
    # The destination filenames MUST match what's in the workflow JSON.
    print(f"Copying {args.user_image} to {os.path.join(INPUT_DIR, 'guy.png')}")
    shutil.copy(args.user_image, os.path.join(INPUT_DIR, "guy.png"))
    
    print(f"Copying {args.jersey_image} to {os.path.join(INPUT_DIR, 'jersey.png')}")
    shutil.copy(args.jersey_image, os.path.join(INPUT_DIR, "jersey.png"))

    print(f"Copying {args.filter_image} to {os.path.join(INPUT_DIR, 'filter.png')}")
    shutil.copy(args.filter_image, os.path.join(INPUT_DIR, "filter.png"))
    
    print("====================================")
    print(f"Inputs prepared in {INPUT_DIR}:")
    for f in os.listdir(INPUT_DIR):
        print(f)
    print("====================================")

    # --- 4. Start Server and Run Workflow ---
    comfyUI.start_server(OUTPUT_DIR, INPUT_DIR)

    try:
        workflow = json.loads(args.workflow_json)
    except json.JSONDecodeError:
        print("Error: Invalid JSON in workflow_json argument.")
        sys.exit(1)

    # The `load_workflow` function will now find the files because they were copied in Step 3.
    wf = comfyUI.load_workflow(workflow)
    
    comfyUI.connect()
    comfyUI.run_workflow(wf)

    # --- 5. Handle Outputs ---
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

if __name__ == "__main__":
    main()