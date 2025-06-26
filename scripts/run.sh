#!/bin/bash
set -e

# Start the ComfyUI server in the background on the CPU
echo "Starting ComfyUI server in CPU mode..."
python ComfyUI/main.py --listen 0.0.0.0 &

# Store the server's process ID for a clean shutdown later
SERVER_PID=$!
echo "ComfyUI server started with PID: $SERVER_PID"

# Wait for the server to initialize. 10-15 seconds is usually safe for a CPU server.
echo "Waiting for server to be ready..."
sleep 15

# Execute the Python prediction script, passing all command-line arguments to it
echo "Running prediction script..."
python predict_docker.py "$@"

# After the script finishes, shut down the ComfyUI server gracefully
echo "Prediction finished. Shutting down ComfyUI server..."
kill $SERVER_PID
wait $SERVER_PID
echo "Server shut down."