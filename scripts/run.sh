#!/bin/bash
set -e

echo "Running prediction script..."
# The `if __name__ == "__main__":` block in predict.py will be executed.
# It calls setup() which starts the server, then calls predict().
python3 /app/predict.py "$@"

echo "Prediction script finished."