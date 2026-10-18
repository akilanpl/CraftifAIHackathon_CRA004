#!/usr/bin/env bash
# HOST terminal only. No installation, GPU, compiler, PipeGen or system changes.
set -euo pipefail
cd "$(dirname "$0")/.."
/usr/local/libexec/pipegen-user-storage-check
export SENTINEL_EVAL_HOME="${SENTINEL_EVAL_HOME:-/mnt/seagate4/PipeGenHackathon/independent-ai-monitor/evaluation-2026-10-18}"
common_dir="$(git rev-parse --path-format=absolute --git-common-dir)"
app_python="${SENTINEL_EVAL_PYTHON:-$(dirname "$common_dir")/.venv/bin/python}"
video="${SENTINEL_EVAL_VIDEO:-/home/vijayababu/.pipegen/factory-inputs/warehouse-workers-4281405-1080p.mp4}"
ai_home="${SENTINEL_AI_HOME:-/mnt/seagate4/PipeGenHackathon/independent-ai-monitor}"
"$app_python" - <<'PY'
import os,pathlib,shutil
root=pathlib.Path(os.environ['SENTINEL_EVAL_HOME'])
existing=root
while not existing.exists():existing=existing.parent
if existing.stat().st_dev==pathlib.Path('/').stat().st_dev:raise SystemExit('Evaluation data must use external storage')
if shutil.disk_usage('/').free<1024**3 or shutil.disk_usage(existing).free<20*1024**3:raise SystemExit('Storage reserves below required minimums')
print('Evaluation storage reserves verified; no dependencies will be installed.')
PY
if [[ ! -f "$SENTINEL_EVAL_HOME/dataset/dataset-manifest.json" ]]; then
  /usr/bin/python3 evaluation/prepare_dataset.py --video "$video" --output "$SENTINEL_EVAL_HOME/dataset"
fi
extra_args=()
if [[ -f "$SENTINEL_EVAL_HOME/reports/predictions.json" ]]; then extra_args+=(--reuse-predictions); fi
"$app_python" evaluation/run_evaluation.py --dataset "$SENTINEL_EVAL_HOME/dataset" --model "$ai_home/models/yolov8m.onnx" --dependencies "$ai_home/dependencies" --report-dir "$SENTINEL_EVAL_HOME/reports" "${extra_args[@]}"
"$app_python" - <<'PY'
import shutil
if shutil.disk_usage('/').free<1024**3:raise SystemExit('Root reserve fell below1GiB; stop further work')
print('HOST EVALUATION FINISHED; formal accuracy remains pending until approved human annotations exist.')
PY
printf '\nTo review, run in the host terminal:\n/usr/bin/python3 -m http.server 5190 --bind 127.0.0.1 --directory %q\nThen open http://127.0.0.1:5190/\n' "$SENTINEL_EVAL_HOME/dataset"
