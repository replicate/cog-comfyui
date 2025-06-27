#!/bin/bash
set -e

# This script's only job is to execute the main Python application.
# The "$@" passes all arguments from the `docker run` command along.
python3 /app/predict.py "$@"