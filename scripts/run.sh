#!/bin/bash
set -e

# Start the ComfyUI server in the background
echo "Starting ComfyUI server in CPU mode..."
python3 /app/ComfyUI/main.py --listen 0.0.0.0 --cpu &

# Store the server's process ID
SERVER_PID=$!
echo "ComfyUI server started with PID: $SERVER_PID"

# --- NEW: Robust readiness check ---
echo "Waiting for ComfyUI server to be ready..."
ATTEMPTS=0
MAX_ATTEMPTS=60 # Wait for a maximum of 60 seconds

while ! curl -s -o /dev/null "http://127.0.0.1:8188/history/1"; do
    ATTEMPTS=$((ATTEMPTS + 1))
    if [ $ATTEMPTS -ge $MAX_ATTEMPTS ]; then
        echo "ComfyUI server failed to start within $MAX_ATTEMPTS seconds."
        # Optional: Print server logs for debugging
        # tail -n 50 /path/to/comfyui/server.log 
        kill $SERVER_PID
        exit 1
    fi
    sleep 1
done

echo "ComfyUI server is ready."
# --- End of readiness check ---

# Execute the Python prediction script
echo "Running prediction script..."
python3 /app/predict.py "$@"

# Shut down the server
echo "Prediction finished. Shutting down ComfyUI server..."
kill $SERVER_PID
wait $SERVER_PID
echo "Server shut down."