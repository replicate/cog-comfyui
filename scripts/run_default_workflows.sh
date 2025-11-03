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

# Extract (url, expected_error) pairs from YAML (ignore commented lines)
declare -a ITEMS=()
expected=""
while IFS= read -r line; do
  # Skip commented lines
  [[ "$line" =~ ^[[:space:]]*# ]] && continue
  if [[ "$line" =~ ^[[:space:]]*-[[:space:]]*error_contains:[[:space:]]*"?(.*)"?[[:space:]]*$ ]]; then
    expected="${BASH_REMATCH[1]}"
    continue
  fi
  if [[ "$line" =~ ^[[:space:]]*workflow_json:[[:space:]]*(https?://.*)$ ]]; then
    url="${BASH_REMATCH[1]}"
    ITEMS+=("${url}||||${expected}")
    expected=""
  fi
done < "$DEFAULT_YAML"

if [ ${#ITEMS[@]} -eq 0 ]; then
  echo "No workflow_json entries found in $DEFAULT_YAML" >&2
  exit 1
fi

echo "Found ${#ITEMS[@]} workflows. Running sequentially..."

idx=0
for item in "${ITEMS[@]}"; do
  idx=$((idx+1))
  IFS='||||' read -r url expected_error <<< "$item"
  echo "[$idx/${#ITEMS[@]}] Running: $url"

  # Prefer local file if URL points to this repo's examples
  wf_arg="workflow_json=$url"
  if [[ "$url" =~ ^https://raw.githubusercontent.com/.*/examples/api_workflows/(.*\.json)$ ]]; then
    rel_path="${BASH_REMATCH[1]}"
    local_path="$ROOT_DIR/examples/api_workflows/$rel_path"
    if [ -f "$local_path" ]; then
      echo "Using local file: $local_path"
      wf_arg="workflow_json=@$local_path"
    fi
  fi

  output=""
  if ! output=$(cog predict -i "$wf_arg" -i return_temp_files=true 2>&1); then
    if [ -n "$expected_error" ] && echo "$output" | grep -q "$expected_error"; then
      echo "[EXPECTED ERROR] $url"
      echo "[EXPECTED ERROR] $url" >> "$LOG_FILE"
      echo "$output" >> "$LOG_FILE"
      echo "--" >> "$LOG_FILE"
      continue
    fi
    echo "[ERROR] $url" | tee -a "$LOG_FILE" >&2
    echo "$output" >> "$LOG_FILE"
    echo "--" >> "$LOG_FILE"
    continue
  else
    if [ -n "$expected_error" ]; then
      echo "[UNEXPECTED SUCCESS] $url (expected error containing: $expected_error)" | tee -a "$LOG_FILE"
      continue
    fi
  fi

  echo "[OK] $url"
done

echo "Done. Errors (if any) logged to: $LOG_FILE"
