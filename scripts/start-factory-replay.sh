#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export SENTINEL_MODE=replay
export SENTINEL_DATASET_PROFILE=factory
# No filename is discovered and no historical asset is substituted.
# Leave SENTINEL_PROFILE_PATH unset to serve an honest PENDING profile.
if [[ -n "${SENTINEL_PROFILE_PATH:-}" ]]; then
  if .venv/bin/python scripts/validate_dataset_profile.py "$SENTINEL_PROFILE_PATH" --scene factory; then
    :
  else
    printf '%s\n' 'Factory assets are pending or invalid; playback remains blocked.' >&2
  fi
fi
exec scripts/start-backend.sh "$@"
