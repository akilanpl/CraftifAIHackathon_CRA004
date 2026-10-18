#!/usr/bin/env bash
# Run only after a human independently completes and approves all 41 annotations.
set -euo pipefail
if [[ $# -ne 1 ]]; then
  printf 'Usage: bash %s /absolute/path/annotations-human-reviewed.json\n' "$0" >&2
  exit 2
fi
cd "$(dirname "$0")/.."
/usr/local/libexec/pipegen-user-storage-check
common_dir="$(git rev-parse --path-format=absolute --git-common-dir)"
app_python="${SENTINEL_EVAL_PYTHON:-$(dirname "$common_dir")/.venv/bin/python}"
ai_home="${SENTINEL_AI_HOME:-/mnt/seagate4/PipeGenHackathon/independent-ai-monitor}"
eval_home="${SENTINEL_EVAL_HOME:-$ai_home/evaluation-2026-10-18}"
annotations="$1"
# Validate the attestation and storage BEFORE creating a new report directory.
"$app_python" - "$eval_home" "$annotations" <<'PY'
import json,pathlib,shutil,sys
from evaluation.run_evaluation import load_review
root=pathlib.Path(sys.argv[1]); annotation=pathlib.Path(sys.argv[2])
if not annotation.is_absolute():raise SystemExit('Provide the exact absolute exported annotation path')
manifest=json.loads((root/'dataset/dataset-manifest.json').read_text())
images,approved,_=load_review(manifest,json.loads(annotation.read_text()))
if not approved or len(images)!=41:raise SystemExit('STOP: all 41 independently human-reviewed annotations and complete attestation are required')
if root.stat().st_dev==pathlib.Path('/').stat().st_dev:raise SystemExit('Reports must use external storage')
if shutil.disk_usage('/').free<1024**3 or shutil.disk_usage(root).free<20*1024**3:raise SystemExit('Required storage reserves unavailable')
print('Complete manual review attestation and storage validated; reusing recorded predictions only.')
PY
report_dir="$(mktemp -d "$eval_home/reviewed-reports-XXXXXXXX")"
cp -- "$eval_home/reports/predictions.json" "$report_dir/predictions.json"
cp -- "$annotations" "$report_dir/annotations-human-reviewed.json"
"$app_python" evaluation/run_evaluation.py --dataset "$eval_home/dataset" --model "$ai_home/models/yolov8m.onnx" --dependencies "$ai_home/dependencies" --report-dir "$report_dir" --annotations "$report_dir/annotations-human-reviewed.json" --reuse-predictions
printf 'Reviewed reports (original pending reports preserved): %s\n' "$report_dir"
