#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
RUNTIME_NODE="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin"
if ! command -v node >/dev/null && [[ -x "$RUNTIME_NODE/node" ]]; then
  export PATH="$RUNTIME_NODE:$PATH"
fi
.venv/bin/python -m pytest -q
cd frontend
node tests/domain.test.ts
node tests/replaySync.test.ts
node tests/replayResources.test.ts
node tests/datasetScope.test.ts
node tests/aiCamera.test.ts
node tests/cameraDevices.test.ts
node tests/modelEvidence.test.ts
node tests/analyticsPresentation.test.ts
node tests/zoneEditor.test.ts
node tests/aiMonitorPresentation.test.ts
node tests/integrationHealth.test.ts
node node_modules/typescript/bin/tsc -b
node node_modules/vite/bin/vite.js build
