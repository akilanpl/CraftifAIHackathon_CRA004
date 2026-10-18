# Next PipeGen capture: minimum integration handoff

Status: **awaiting genuine output**. The external operator reports PipeGen 0.5.1 at Requirement Inputs with DeepStream 7.1 downloaded. This application chat has not independently verified that GUI/runtime status. No native mapping is configured here.

The complete field contract is in `pipegen-handoff.md`; this note prioritizes what to preserve during the next real run.

## Before generating the pipeline

Ask the generated pipeline to expose **structured per-frame person detections with stable tracker IDs**, including confident outside observations and empty frames, in addition to an annotated display. Boxes or screenshots alone cannot feed Sentinel's incident engine. Select an actual supported metadata output available in the generated pipeline; do not assume a specific PipeGen node, sink, JSON layout or GUI control exists.

A local JSONL file is sufficient if that output is actually supported. No MQTT/Kafka service is needed for this application's first integration. Keep the original records unchanged, and supply their absolute output path. If the producer emits a different format or transport, preserve a small genuine sample before implementing a converter. Do not substitute hand-written example records.

Keep the input on verified external storage. Record both host and runtime/container file paths; an accessible host path does not establish that the runtime sees the same path. The setup/PipeGen operator owns container mappings. This application chat does not alter them.

## First successful run: preserve these facts

- Exact generated source dimensions and the dimensions/coordinate space attached to object boxes. Preserve any resize, padding, crop or rotation configuration.
- Tracker configuration and actual assigned IDs, including any untracked sentinel and ID reset/reuse behavior. Preserve the model's actual person label/class mapping and confidence semantics.
- Timestamp semantics. A file's playback PTS/frame index is not Unix wall time. If only relative time exists, capture a verified run start wall-clock anchor and the corresponding source-time origin; do not label PTS as epoch or invent capture dates. The current mapper requires wall-clock ISO or explicitly configured Unix units; relative-time conversion needs verified custom handling.
- Whether output is a complete frame snapshot, changed objects only, one record per object, a batch, or already-generated zone events. Object-only deltas need verified grouping/frame boundaries before the current one-frame API can consume them.
- If native analytics is chosen, preserve the actual zone IDs, geometry/reference point, entry/exit meaning, unique event IDs and retry behavior. Keep one authoritative event path; do not independently count native and derived entries.
- If displaying video in the browser, determine whether an actual browser-playable HTTP(S) output exists. A raw RTSP output cannot be assigned directly to the dashboard's HTML video element. Metadata-only operation is sufficient to test real incidents and must retain the Detection Metadata View label.

## Minimum sample package to return

1. A small untouched sequence showing outside → entry → repeated inside → visible exit → re-entry, preferably including two people and an empty frame. Include approximately 10–30 consecutive records around transitions if available; never omit the frame context needed to interpret object records.
2. The generated pipeline/export files and the above field meanings, input/output absolute paths and actual run ID/start time.
3. Actual Requirement/IR/model/FP16 compiler report/DeepStream evidence as it becomes available. Failed or unfinished stages remain PENDING.

No native field mapping should begin before that package is inspected. Validate converted output locally with `scripts/validate_metadata.py` before live ingestion. Create the matching camera's zones in the separate live database, then prove one real entry/hold/exit/re-entry sequence end to end. GPU metrics and real-integration evidence remain unavailable until observed.
