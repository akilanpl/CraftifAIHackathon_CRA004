#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export SENTINEL_API_TARGET="${SENTINEL_API_TARGET:-http://127.0.0.1:8001}"
exec bash scripts/start-frontend.sh --port "${SENTINEL_FRONTEND_PORT:-5174}" --strictPort "$@"
