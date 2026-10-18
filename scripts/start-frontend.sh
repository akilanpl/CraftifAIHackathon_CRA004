#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../frontend"
RUNTIME_NODE="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin"
if ! command -v node >/dev/null && [[ -x "$RUNTIME_NODE/node" ]]; then
  export PATH="$RUNTIME_NODE:$PATH"
fi
if ! command -v node >/dev/null; then
  echo 'Node.js is required. See docs/setup.md.' >&2
  exit 1
fi
if [[ ! -f node_modules/vite/bin/vite.js ]]; then
  echo 'Install frontend dependencies first. See docs/setup.md.' >&2
  exit 1
fi
exec node node_modules/vite/bin/vite.js --host 127.0.0.1 "$@"
