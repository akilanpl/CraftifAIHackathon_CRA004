# Independent CPU evaluation and human annotation

## Current verified state

41 real warehouse frames were prepared and inferred on the host using the unchanged YOLOv8m ONNX model, ONNX Runtime 1.31.0 CPUExecutionProvider. Median processing latency was 629.744 ms (range 600.455–775.798 ms). The initial inference run used zero approved labels. The latest available exported file is PARTIAL with 1/41 marked reviewed; it is rejected for full-dataset evaluation. Formal accuracy is PENDING HUMAN REVIEW. CPU timings are not TensorRT or full PipeGen pipeline benchmarks.

External experiment root:
`/mnt/seagate4/PipeGenHackathon/independent-ai-monitor/evaluation-2026-10-18`

The source video SHA256 is `14fb11cda9d031b497755195c04f6781df3a579d9044155114a3923cc5f43671`; model SHA256 is `8db1e3bb5e53410eb79da1e166fa3e1a05d6d1ff29df33af7345f2f3b73e20d7`. The dataset manifest records every exact review image hash, source index and PTS. Frames are 960×540 JPEGs inferred as such, not full-resolution accuracy samples. Forty uniformly sampled frames plus frame 106 total 41; this is one short moving-camera clip, not an independent deployment benchmark.

## Open the annotation page

Already running: <http://127.0.0.1:5190/>. If it needs restarting, use a host terminal:

```bash
/usr/bin/python3 -m http.server 5190 --bind 127.0.0.1 --directory /mnt/seagate4/PipeGenHackathon/independent-ai-monitor/evaluation-2026-10-18/dataset
```

This standalone review tool is separate from the application frontend. It loads images, `dataset-manifest.json`, and the initially empty `annotations.json`. It does not load predictions or change server files. Manual progress is stored in this browser's local storage for this dataset; keep the same browser and origin and export backups. Do not clear browser storage while reviewing.

## Human review instructions — all 41 frames

1. Enter your actual reviewer name. Start at the first frame using the frame dropdown.
2. Drag a tight box around **every visible real person**. Include partially visible people using their visible extent consistently; do not guess hidden full bodies. Release to create each box. Green boxes are your manual annotations, not AI proposals.
3. Leave shelving, boxes, reflections and background unboxed. You do not approve or reject prefilled AI boxes: there are none. Later matching against these independent labels will classify model detections as TP/FP/FN.
4. Use **Delete person box** or **Clear boxes** to correct mistakes. If the frame truly has no visible people, tick **I inspected this frame: no visible people**. An unreviewed empty list is unknown, never a negative label.
5. Click **Mark this frame human-reviewed**, then **Next**. Review all 41 frames, including source frame 106. Edits invalidate that frame's prior approval.
6. Check the counter says **41/41 frames human-reviewed**. Click **Export annotation + human-review record**. Keep the downloaded `annotations-human-reviewed.json`. Partial exports are valid backups but cannot produce formal metrics.
7. Send the exact exported local path and explicitly confirm you independently drew and approve those labels. Do not rename model predictions as ground truth. Human review records contain the reviewer name and time; review those fields before sharing publicly.

The complete frame list is `dataset/dataset-manifest.json`; every image record in the exported annotations requires human review. Do not edit `reports/predictions.json` to create labels. Qualitative prediction overlays in `reports/comparisons/` are analysis outputs, excluded from the blind annotation workflow.

## After human approval

The evaluator supports `--annotations /absolute/path/annotations-human-reviewed.json --reuse-predictions`. Reuse the exact original predictions; no second inference or production threshold change is needed. Run from this audit worktree in a HOST terminal, keeping reviewed outputs separate from the pending snapshot:

```bash
/usr/local/libexec/pipegen-user-storage-check
cd /home/vijayababu/Documents/Codex/2026-10-18/files-pasted-by-the-user-mission/work/ai-evaluation-worktree
```

After the reviewed file path is provided, run:

```bash
bash scripts/evaluate-reviewed-host.sh /absolute/path/annotations-human-reviewed.json
```

This validates dataset/video/image hashes, dimensions, all 41 manual approvals and human attestation, then reuses `reports/predictions.json` and writes reviewed reports to a new uniquely named external directory. It preserves the initial pending reports and exported annotation file; no second inference is run. No annotations are automatically approved by the evaluator. Incomplete review keeps formal metrics null.

Metrics: confidence-ranked per-image person IoU matching at 0.5 gives TP/FP/FN, precision, recall and F1 for thresholds 0.25/0.40/0.50/0.60/0.70. Person-only AP uses 101-point interpolated precision at IoU 0.50 and mean IoU 0.50:0.05:0.95, over the same bounded post-NMS predictions. This is not the full COCO evaluator: no crowd/ignore/area/maxDets handling, no multiclass benchmark, and the 100-candidate cap/NMS 0.45 affect recall. Empty-GT AP is undefined. Threshold selection on this same small dataset is exploratory, not an independent held-out validation.

## Reproduce the initial experiment

```bash
bash scripts/run-evaluation-host.sh
```

This checks storage, installs nothing, preserves existing dataset/annotations, reuses predictions when present, and uses the existing external CPU dependencies. External writes require the host terminal; do not alter mount permissions. Keep at least 1 GiB free on root and 20 GiB on external storage. The source video, original PipeGen model, V2 ROI, SQLite history, live monitor and production settings are untouched.

See `evidence/evaluation/alert-robustness-tests.json` for 20 business-logic cases (16 verified contracts and four documented limitations), and `docs/evaluation/int8-feasibility.md` for the read-only assessment. INT8 benchmark, Jetson deployment and physical USB hardware testing remain NOT TESTED.
