# predict.py (Final Version - Dynamic Inputs)

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

def update_workflow_image_inputs(workflow, args):
    """
    Dynamically update the 'image' field in all LoadImage nodes
    based on the command-line arguments provided.
    """
    # This mapping connects the workflow's expected filename to the
    # command-line argument that provides the file.
    filename_to_arg_map = {
        "guy.png": args.user_image,
        "jersey.png": args.jersey_image,
        "filter.png": args.filter_image,
    }

    for node in workflow.values():
        if node.get("class_type") == "LoadImage":
            original_filename = node["inputs"].get("image")
            if original_filename in filename_to_arg_map:
                new_file_path = filename_to_arg_map[original_filename]
                if new_file_path and new_file_path.exists():
                    # The new filename is just the final part of the path
                    new_filename = os.path.basename(new_file_path)
                    print(f"Updating workflow: Replacing '{original_filename}' with '{new_filename}'")
                    node["inputs"]["image"] = new_filename
    return workflow


def main():
    # --- 1. Parse Arguments ---
    parser = argparse.ArgumentParser(description="Run a ComfyUI workflow.")
    parser.add_argument("--workflow_json", type=str, required=True)
    parser.add_argument("--user_image", type=Path, required=False)
    parser.add_argument("--jersey_image", type=Path, required=False)
    parser.add_argument("--filter_image", type=Path, required=False)
    parser.add_argument("--output_format", type=str, default="webp")
    parser.add_argument("--output_quality", type=int, default=80)
    parser.add_argument("--final_output_path", type=str, default="/app/final_outputs")
    args = parser.parse_args()

    # --- 2. Start Server ---
    server_command = [
        "python3", "/app/ComfyUI/main.py", "--listen", "0.0.0.0", "--cpu",
        "--output-directory", OUTPUT_DIR, "--input-directory", INPUT_DIR, "--disable-metadata"
    ]
    print("Starting ComfyUI server...")
    server_process = subprocess.Popen(server_command)
    print(f"ComfyUI server started with PID: {server_process.pid}")

    comfyUI = ComfyUI("127.0.0.1:8188")

    try:
        # --- 3. Wait for Server ---
        for i in range(60):
            if comfyUI.is_server_running():
                print("Server is ready.")
                break
            time.sleep(1)
        else:
            raise TimeoutError("ComfyUI server failed to start")
        
        comfyUI.cleanup(ALL_DIRECTORIES)

        # --- 4. Prepare Inputs ---
        # Copy files from their mounted location to the INPUT_DIR that ComfyUI watches.
        # We use the basename from the provided path as the destination filename.
        if args.user_image and args.user_image.exists():
            shutil.copy(args.user_image, os.path.join(INPUT_DIR, os.path.basename(args.user_image)))
        if args.jersey_image and args.jersey_image.exists():
            shutil.copy(args.jersey_image, os.path.join(INPUT_DIR, os.path.basename(args.jersey_image)))
        if args.filter_image and args.filter_image.exists():
            shutil.copy(args.filter_image, os.path.join(INPUT_DIR, os.path.basename(args.filter_image)))
        
        # --- 5. Load and Dynamically Update Workflow ---
        workflow = json.loads(args.workflow_json)
        wf = update_workflow_image_inputs(workflow, args)
        
        # Now call the original load_workflow which will perform the final checks
        wf = comfyUI.load_workflow(wf)

        # --- 6. Run Workflow and Handle Outputs ---
        comfyUI.connect()
        comfyUI.run_workflow(wf)
        
        output_files = comfyUI.get_files([OUTPUT_DIR, "ComfyUI/temp"])
        optimised_files = optimise_images.optimise_image_files(
            args.output_format, args.output_quality, output_files
        )
        final_output_dir = Path(args.final_output_path)
        final_output_dir.mkdir(parents=True, exist_ok=True)
        
        print("--- Copying final outputs ---")
        for file_path in optimised_files:
            if file_path.is_file():
                shutil.copy(file_path, final_output_dir)
                print(f"Copied {file_path.name} to {final_output_dir}")

        print("\nPrediction successful.")

    finally:
        # --- 7. Shutdown ---
        print("Prediction process finished. Shutting down ComfyUI server...")
        server_process.terminate()
        server_process.wait()
        print("Server shut down.")

if __name__ == "__main__":
    main()