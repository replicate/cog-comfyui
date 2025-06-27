#!/bin/bash
set -e

# The Python script handles everything.
python3 /app/predict.py "$@"