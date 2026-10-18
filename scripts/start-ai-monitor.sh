#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
ai_home="${SENTINEL_AI_HOME:-/mnt/seagate4/PipeGenHackathon/independent-ai-monitor}"
if [[ -d "$ai_home" ]]; then
  export SENTINEL_AI_HOME="$ai_home"
  if [[ -z "${SENTINEL_AI_MODEL_PATH+x}" ]]; then
    export SENTINEL_AI_MODEL_PATH="$ai_home/models/yolov8m.onnx"
  fi
  if [[ -z "${SENTINEL_AI_DEPENDENCIES_PATH+x}" ]]; then
    export SENTINEL_AI_DEPENDENCIES_PATH="$ai_home/dependencies"
  fi
  if [[ -z "${SENTINEL_AI_DATA_DIR+x}" ]]; then
    export SENTINEL_AI_DATA_DIR="$ai_home/sessions"
  fi
fi
exec .venv/bin/python -m uvicorn backend.monitor_main:app --host 127.0.0.1 --port "${AI_PORT:-8004}" "$@"
