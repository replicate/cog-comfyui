#!/bin/bash

docker run -it --rm \
  -e REPLICATE_API_TOKEN \
  -v "$(pwd)/inputs:/inputs" \
  -v "$(pwd)/inputs/comfyui_full_workflow.json:/app/workflow.json" \
  -v "$(pwd)/final_outputs:/app/final_outputs" \
  lbbw-trikot-comfyui-cpu:latest \
  --workflow_json_file /app/workflow.json \
  --user_image /inputs/guy.png \
  --jersey_image /inputs/jersey.png \
  --filter_image /inputs/filter.png \
  --location_image /inputs/location.png \
  --final_output_path /app/final_outputs