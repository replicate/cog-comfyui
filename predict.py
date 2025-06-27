# predict.py (Final Version with S3 Upload)

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

# Define temporary directories inside the container
OUTPUT_DIR = "/tmp/outputs"
INPUT_DIR = "/tmp/inputs"
ALL_DIRECTORIES = [OUTPUT_DIR, INPUT_DIR, "ComfyUI/temp"]

def main():
    # --- 1. Parse All Arguments ---
    parser = argparse.ArgumentParser(description="Generate an image and upload it to S3.")
    parser.add_argument("--workflow_json_file", type=Path, required=True)
    parser.add_argument("--user_image", type=Path, required=False)
    parser.add_argument("--jersey_image", type=Path, required=False)
    parser.add_argument("--filter_image", type=Path, required=False)
    parser.add_argument("--location_image", type=Path, required=False)
    
    # NEW: S3 URL argument
    parser.add_argument("--s3_url", type=str, required=True, help="The destination S3 URL for the final image.")
    
    # Optional output formatting
    parser.add_argument("--output_format", type=str, default="webp")
    parser.add_argument("--output_quality", type=int, default=80)
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
            raise TimeoutError("ComfyUI server did not start")

        # --- 4. Prepare Environment and Inputs ---
        comfyUI.cleanup(ALL_DIRECTORIES)
        
        if args.user_image and args.user_image.exists():
            shutil.copy(args.user_image, os.path.join(INPUT_DIR, "guy.png"))
        if args.jersey_image and args.jersey_image.exists():
            shutil.copy(args.jersey_image, os.path.join(INPUT_DIR, "jersey.png"))
        if args.filter_image and args.filter_image.exists():
            shutil.copy(args.filter_image, os.path.join(INPUT_DIR, "filter.png"))
        if args.location_image and args.location_image.exists():
            shutil.copy(args.location_image, os.path.join(INPUT_DIR, "location.png"))

        # --- 5. Load and Run Workflow ---
        with open(args.workflow_json_file, 'r') as f:
            workflow_data = json.load(f)
            
        wf = comfyUI.load_workflow(workflow_data)
        comfyUI.connect()
        comfyUI.run_workflow(wf)

        # --- 6. Process and Upload Output ---
        output_files = comfyUI.get_files([OUTPUT_DIR, "ComfyUI/temp"])

        if not output_files:
            raise RuntimeError("Workflow did not generate any output files.")

        # Assume the first generated file is the one we want to upload
        generated_file = output_files[0]
        
        # Note: Optimization logic is removed for clarity, but you can add it back here
        # if you need to convert to webp before uploading.
        # For now, we upload the file as-is.
        
        print(f"Found generated file: {generated_file}")
        print(f"Uploading to S3 URL: {args.s3_url}")

        upload_command = ["aws", "s3", "cp", str(generated_file), args.s3_url]
        subprocess.run(upload_command, check=True)

        print("Upload to S3 successful.")
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