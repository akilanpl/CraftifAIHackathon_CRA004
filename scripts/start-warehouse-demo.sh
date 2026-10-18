#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# This helper is pinned to the verified Warehouse FP16 v2 execution.
export SENTINEL_WAREHOUSE_VIDEO="${1:-${SENTINEL_WAREHOUSE_VIDEO:-/home/vijayababu/.pipegen/factory-inputs/warehouse-workers-4281405-1080p.mp4}}"
export SENTINEL_PROFILE_PATH="$PWD/config/local-warehouse-fp16-v2.json"
.venv/bin/python - <<'PY'
import json,os
from pathlib import Path
root=Path.cwd()
profile=json.loads((root/'examples/warehouse-profile.json').read_text())
profile['video_path']=str(Path(os.environ['SENTINEL_WAREHOUSE_VIDEO']).resolve())
profile['metadata_path']=str(root/'evidence/06-real-metadata/warehouse-fp16-v2-metadata.json')
target=Path(os.environ['SENTINEL_PROFILE_PATH'])
target.parent.mkdir(parents=True,exist_ok=True)
# Never replace a user's manually reviewed local configuration.
if target.exists():
    existing=json.loads(target.read_text())
    if existing!=profile:
        raise SystemExit('Existing local warehouse manifest differs. Review it or use SENTINEL_PROFILE_PATH with start-factory-replay.sh; no file was overwritten.')
else:
    target.write_text(json.dumps(profile,indent=2)+'\n')
PY
export PORT="${PORT:-8003}"
exec scripts/start-factory-replay.sh
