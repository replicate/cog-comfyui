#!/bin/bash
set -e

# The Python script will handle everything, including starting and stopping the server.
# "$@" passes all command-line arguments from `docker run` to the python script.
python3 /app/predict.py "$@"