#!/usr/bin/env bash
# Dependencies: existing .venv with requirements-lock.txt; no GPU/model/video needed.
set -euo pipefail
cd "$(dirname "$0")/../.."
if [[ ! -x .venv/bin/python ]]; then
  echo 'Create .venv and install requirements-lock.txt first; see submission/mac-validation.md.' >&2
  exit 1
fi
exec .venv/bin/python scripts/mac/recorded_e2e.py "$@"
