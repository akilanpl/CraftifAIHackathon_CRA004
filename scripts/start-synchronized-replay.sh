#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
metadata=${1:-${SENTINEL_REPLAY_PATH:-/home/vijayababu/.pipegen/varunvbabu/c74acf17-f432-4f7a-ac13-c48b447ccf1a/output/metadata.json}}
video=${2:-${SENTINEL_REPLAY_VIDEO:-}}
if [[ -z "$video" ]]; then
  for candidate in /home/vijayababu/Videos/people-crossing.mp4 /mnt/seagate4/PipeGenHackathon/demo/people-crossing.mp4; do
    if [[ -r "$candidate" ]]; then video=$candidate; break; fi
  done
fi
export SENTINEL_REPLAY_PATH="$metadata" SENTINEL_REPLAY_VIDEO="$video"
if [[ ! -x .venv/bin/python ]]; then echo 'Install the project virtual environment first; see docs/setup.md.' >&2; exit 1; fi
.venv/bin/python - <<'PY'
import hashlib,os,sys
from pathlib import Path
pairs=[('SENTINEL_REPLAY_VIDEO','cfb10db5adb8869240e78ef68185f429a52efac1054b26aca4ccc3534c6094b5'),('SENTINEL_REPLAY_PATH','ae10cfba371d2d553f4804058240e56ade5653c83c86916f354892c55df6d941')]
for setting,expected in pairs:
    p=Path(os.environ[setting])
    if not p.is_file() or not os.access(p,os.R_OK):sys.exit(setting+' is not a readable file')
    with p.open('rb') as handle:
        digest=hashlib.file_digest(handle,'sha256').hexdigest() if hasattr(hashlib,'file_digest') else hashlib.sha256(handle.read()).hexdigest()
    if digest!=expected:sys.exit(setting+' does not match the verified video/metadata pair; inspect timestamps and configure a new verified mapping explicitly')
print('Verified original video and metadata SHA-256. Applying inspected +33,366,700 ns PTS offset.')
PY
export SENTINEL_REPLAY_VIDEO_PTS_OFFSET_NS=33366700
export SENTINEL_REPLAY_VIDEO_TOLERANCE_NS=8350000
export PORT="${PORT:-8001}"
exec bash scripts/start-real-replay.sh "$metadata"
