#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
metadata=${1:-${SENTINEL_REPLAY_PATH:-}}
if [[ -z "$metadata" || ! -r "$metadata" ]]; then
  echo 'Usage: bash scripts/start-real-replay.sh /absolute/path/to/genuine/metadata.json' >&2
  exit 1
fi
export SENTINEL_MODE=replay
export SENTINEL_REPLAY_PATH="$metadata"
export SENTINEL_REPLAY_CAMERA="${SENTINEL_REPLAY_CAMERA:-cam-01}"
export SENTINEL_DB_PATH="${SENTINEL_DB_PATH:-$PWD/data/pipegen-replay.sqlite3}"
exec bash scripts/start-backend.sh
