#!/bin/bash
set -e

# Change to the ComfyUI directory before starting the server
cd /home/user/app/ComfyUI

# Start the ComfyUI server in the background
echo "Starting ComfyUI server in CPU mode..."
# Use python3 executable explicitly and start server.
python3 main.py --listen 0.0.0.0 &

# Store the server's process ID for a clean shutdown later
SERVER_PID=$!
echo "ComfyUI server started with PID: $SERVER_PID"

# Go back to the main app directory to run the prediction script
cd /home/user/app

# Wait for the server to initialize
echo "Waiting for server to be ready..."
sleep 15

# Execute the Python prediction script, passing all command-line arguments to it
echo "Running prediction script..."
python3 predict_docker.py "$@"

# After the script finishes, shut down the ComfyUI server gracefully
echo "Prediction finished. Shutting down ComfyUI server..."
kill $SERVER_PID
wait $SERVER_PID
echo "Server shut down."