#!/usr/bin/env bash
# Run in the HOST terminal. Does not change mounts, PipeGen, Docker or GPU software.
set -euo pipefail
cd "$(dirname "$0")/.."
/usr/local/libexec/pipegen-user-storage-check
export SENTINEL_AI_HOME="${SENTINEL_AI_HOME:-/mnt/seagate4/PipeGenHackathon/independent-ai-monitor}"
MODEL_SOURCE="${SENTINEL_AI_MODEL_SOURCE:-/home/vijayababu/.pipegen/exports/pipegen-warehouse-hazard-sentinel-pipeline/models/yolov8m.onnx}"
RUNTIME_PYTHON="${SENTINEL_AI_SETUP_PYTHON:-$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3}"
mkdir -p "$SENTINEL_AI_HOME"/{dependencies,tmp,models,sessions}
export TMPDIR="$SENTINEL_AI_HOME/tmp"
export PIP_CACHE_DIR="$SENTINEL_AI_HOME/tmp/pip-cache"
export SENTINEL_AI_MODEL_SOURCE="$MODEL_SOURCE"
"$RUNTIME_PYTHON" - <<'PY'
import os,pathlib,shutil
home=pathlib.Path(os.environ['SENTINEL_AI_HOME']).resolve()
if shutil.disk_usage('/').free<1024**3:raise SystemExit('Root reserve below1GiB')
if shutil.disk_usage(home).free<20*1024**3:raise SystemExit('External reserve below20GiB')
if home.stat().st_dev==pathlib.Path('/').stat().st_dev:raise SystemExit('AI dependencies must be on a different external filesystem')
PY
"$RUNTIME_PYTHON" -m pip install --no-cache-dir --target "$SENTINEL_AI_HOME/dependencies" 'onnxruntime==1.31.0' 'numpy==2.5.4' 'pillow==13.0.0'
"$RUNTIME_PYTHON" - <<'PY'
import hashlib,json,os,pathlib,shutil,sys
source=pathlib.Path(os.environ['SENTINEL_AI_MODEL_SOURCE']);home=pathlib.Path(os.environ['SENTINEL_AI_HOME']);target=home/'models/yolov8m.onnx'
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
original=digest(source)
if target.exists():
 if digest(target)!=original:raise SystemExit('Existing application model differs; refusing overwrite')
else:shutil.copyfile(source,target)
assert digest(source)==digest(target)==original
sys.path.insert(0,str(home/'dependencies'))
import onnxruntime as ort
assert 'CPUExecutionProvider' in ort.get_available_providers()
(home/'setup-provenance.json').write_text(json.dumps({'runtime':ort.__version__,'provider':'CPUExecutionProvider','model_sha256':original,'original_unchanged':True},indent=2)+'\n')
assert shutil.disk_usage('/').free>=1024**3 and shutil.disk_usage(home).free>=20*1024**3
print('HOST SETUP PASSED. Original model unchanged. CPU-only runtime available.')
PY
printf '\nNext, from this repository run:\nSENTINEL_AI_HOME=%q ./scripts/start-ai-monitor.sh\n' "$SENTINEL_AI_HOME"
