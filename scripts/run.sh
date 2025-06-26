#!/bin/bash
set -e

# Change to the ComfyUI directory before starting the server
cd /home/user/app/ComfyUI

# --- FIX: Added the --cpu flag ---
# This tells ComfyUI not to look for a GPU.
echo "Starting ComfyUI server in CPU mode..."
python3 main.py --listen 0.0.0.0 --cpu &

# Store the server's process ID
SERVER_PID=$!
echo "ComfyUI server started with PID: $SERVER_PID"

# Go back to the main app directory
cd /home/user/app

# Wait for the server to initialize
echo "Waiting for server to be ready..."
sleep 15

# Execute the Python prediction script
echo "Running prediction script..."
python3 predict.py "$@"

# Shut down the ComfyUI server
echo "Prediction finished. Shutting down ComfyUI server..."
kill $SERVER_PID
wait $SERVER_PID
echo "Server shut down."