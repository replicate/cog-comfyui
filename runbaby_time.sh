#!/bin/bash

NUM_JOBS=10

# Check for the REPLICATE_API_TOKEN
if [ -z "$REPLICATE_API_TOKEN" ]; then
    echo "Error: REPLICATE_API_TOKEN environment variable is not set."
    echo "Please run: export REPLICATE_API_TOKEN='your_token_here'"
    exit 1
fi

echo "Starting $NUM_JOBS parallel jobs..."

# The main logic is wrapped in { ... } so that `time` measures the whole block
{
  for i in $(seq 1 $NUM_JOBS)
  do
    # Run each docker command in the background (&)
    # Redirect output to /dev/null to keep the console clean
    docker run --rm \
      -e REPLICATE_API_TOKEN \
      -v "$(pwd)/inputs:/inputs" \
      -v "$(pwd)/lbbw/comfyui_merge_user_jersey.json:/app/workflow.json" \
      -v "$(pwd)/final_outputs/job_$i:/app/final_outputs" \
      lbbw-trikot-comfyui-cpu:latest \
      --workflow_json_file /app/workflow.json \
      --user_image /inputs/guy.png \
      --jersey_image /inputs/jersey.png \
      --filter_image /inputs/filter.png \
      --location_image /inputs/location.png \
      --final_output_path /app/final_outputs > /dev/null 2>&1 &
  done

  # Wait for all background jobs to finish before stopping the timer
  wait
}

echo "All $NUM_JOBS jobs completed."