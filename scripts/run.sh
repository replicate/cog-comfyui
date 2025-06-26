#!/bin/bash
set -e

# --- NEW STEP: Prepare the input directory ---
# Check if a host-mounted directory exists at /host_inputs
# If it does, copy its contents to the application's input directory.
HOST_INPUT_DIR="/host_inputs"
APP_INPUT_DIR="/tmp/inputs"

if [ -d "$HOST_INPUT_DIR" ]; then
  echo "Host inputs found at $HOST_INPUT_DIR. Copying to $APP_INPUT_DIR..."
  # Create the target directory and then copy the contents
  mkdir -p "$APP_INPUT_DIR"
  cp -r $HOST_INPUT_DIR/* "$APP_INPUT_DIR"/
  echo "Copy complete. Contents of $APP_INPUT_DIR:"
  ls -l "$APP_INPUT_DIR"
else
  echo "No host inputs mounted at $HOST_INPUT_DIR. Proceeding..."
fi
# --- END OF NEW STEP ---


echo "Running prediction script..."
# The `if __name__ == "__main__":` block in predict.py will be executed.
# It will call setup() which starts the server, then calls predict().
python3 /app/predict.py "$@"

echo "Prediction script finished."