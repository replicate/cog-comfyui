#!/usr/bin/env bash

set -u

# Runs each workflow_json URL listed in cog-safe-push-configs/default.yaml
# Uses the local Cog environment to run predictions sequentially.
# On failure, logs the error and continues with the next workflow.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_YAML="$ROOT_DIR/cog-safe-push-configs/default.yaml"
LOG_FILE="$ROOT_DIR/scripts/run_default_workflows.log"

if ! command -v cog >/dev/null 2>&1; then
  echo "Error: 'cog' CLI not found in PATH. Install from https://cog.run" >&2
  exit 1
fi

if [ ! -f "$DEFAULT_YAML" ]; then
  echo "Error: default.yaml not found at $DEFAULT_YAML" >&2
  exit 1
fi

# Start fresh log
echo "# run_default_workflows: $(date -u +"%Y-%m-%dT%H:%M:%SZ")" > "$LOG_FILE"

# Extract workflow_json URLs (ignore commented lines)
mapfile -t WORKFLOWS < <(grep -E '^[[:space:]]*workflow_json:[[:space:]]*https?://' "$DEFAULT_YAML" | sed -E 's/^[[:space:]]*workflow_json:[[:space:]]*//')

if [ ${#WORKFLOWS[@]} -eq 0 ]; then
  echo "No workflow_json URLs found in $DEFAULT_YAML" >&2
  exit 1
fi

echo "Found ${#WORKFLOWS[@]} workflows. Running sequentially..."

idx=0
for url in "${WORKFLOWS[@]}"; do
  idx=$((idx+1))
  echo "[$idx/${#WORKFLOWS[@]}] Running: $url"

  # Run prediction. Capture output; on error, append to log and continue.
  if ! output=$(cog predict -i workflow_json="$url" -i return_temp_files=true 2>&1); then
    echo "[ERROR] $url" | tee -a "$LOG_FILE" >&2
    echo "$output" >> "$LOG_FILE"
    echo "--" >> "$LOG_FILE"
    continue
  fi

  # Optionally print minimal success info
  echo "[OK] $url"
done

echo "Done. Errors (if any) logged to: $LOG_FILE"
