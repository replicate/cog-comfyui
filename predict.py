# predict.py (Final Version with Verification)

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
    
    # Arguments for your specific workflow
    parser.add_argument("--user_image", type=Path, required=False, help="Path to the user's image inside the container.")
    parser.add_argument("--jersey_image", type=Path, required=False, help="Path to the jersey image inside the container.")
    parser.add_argument("--filter_image", type=Path, required=False, help="Path to the fallback/filter image inside the container.")
    
    # General output arguments
    parser.add_argument("--output_format", type=str, default="webp")
    parser.add_argument("--output_quality", type=int, default=80)
    parser.add_argument("--final_output_path", type=str, default="/app/final_outputs")
    args = parser.parse_args()

    # --- 2. Start ComfyUI Server in the Background ---
    server_command = [
        "python3", "/app/ComfyUI/main.py",
        "--listen", "0.0.0.0",
        "--cpu",
        "--output-directory", OUTPUT_DIR,
        "--input-directory", INPUT_DIR,
        "--disable-metadata"
    ]
    
    print("Starting ComfyUI server...")
    server_process = subprocess.Popen(server_command)
    print(f"ComfyUI server started with PID: {server_process.pid}")

    # --- 3. Wait for Server to be Ready ---
    comfyUI = ComfyUI("127.0.0.1:8188")
    is_ready = False
    max_retries = 60
    for i in range(max_retries):
        if comfyUI.is_server_running():
            is_ready = True
            print("ComfyUI server is ready.")
            break
        print(f"Waiting for server, attempt {i+1}/{max_retries}...")
        time.sleep(1)
    
    if not is_ready:
        print("Error: ComfyUI server failed to start.")
        server_process.terminate()
        server_process.wait()
        sys.exit(1)
        
    # --- 4. Main Application Logic inside a try...finally block ---
    try:
        # Clean directories (after server is up, to be safe)
        comfyUI.cleanup(ALL_DIRECTORIES)

        # Prepare Inputs if they were provided
        # This copies files from their mounted location to the INPUT_DIR that ComfyUI is configured to use.
        if args.user_image and args.user_image.exists():
            shutil.copy(args.user_image, os.path.join(INPUT_DIR, "guy.jpg"))
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

        # --- VERIFICATION STEP ---
        print("\n--- Verifying final outputs on volume ---")
        if os.path.exists(args.final_output_path) and os.path.isdir(args.final_output_path):
            final_files = os.listdir(args.final_output_path)
            if final_files:
                print(f"Successfully found {len(final_files)} file(s) in {args.final_output_path}:")
                for f in final_files:
                    print(f"- {f}")
            else:
                print(f"Warning: Final output directory {args.final_output_path} is empty.")
        else:
            print(f"Error: Final output directory {args.final_output_path} does not exist.")
        # --- END VERIFICATION STEP ---

        print("\nPrediction successful.")

    finally:
        # --- 5. Ensure Server is Always Shut Down ---
        print("Prediction process finished. Shutting down ComfyUI server...")
        server_process.terminate()
        server_process.wait()
        print("Server shut down.")


if __name__ == "__main__":
    main()