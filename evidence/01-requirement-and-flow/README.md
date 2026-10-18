# Official source and saved factory Requirement checkpoint

The official problem statement and its provenance are preserved in `official-problem-statement.pdf` and `official-source.json`. Those immutable source files were not edited by this checkpoint packaging pass.

## Genuine factory Requirement state

`factory-RequirementState.redacted.json` is a sanitized copy of the real saved Requirement state for project `5b159399-c172-4ac5-8b45-430bd54a4a99`, **Hazard Zone Sentinel — Warehouse FP16 v2**. Both `phase` and `req_stage` are `complete`. Its saved checks report 12 passed, zero failed and zero warned; these are Requirement/handoff checks, not inference or accuracy tests.

Configured facts in the saved state:

- Input: `warehouse-workers-4281405-1080p.mp4`, 1920 × 1080, 25 FPS.
- Requested detector: pretrained YOLOv8m ONNX; requested target: RTX 2060 SUPER, TensorRT FP16.
- Requested tracking: native DeepStream NvDCF.
- Requested zone: `[(0.42,0.74),(0.62,0.74),(0.62,0.86),(0.42,0.86)]` in normalized frame coordinates.
- Requested output: structured JSON metadata, including person observations/tracks and zone analytics.
- No custom training and no INT8 optimization requested in this saved configuration.

The saved scene analysis marks camera motion as moving; a frame-relative polygon is not evidence that the same physical floor area remains fixed through the entire clip. Actual scene alignment and run behavior still require review.

## Integrity and scope

`factory-checkpoint-manifest.json` records original and distributed-copy SHA-256 values, exact file sizes and the redaction policy. The immutable checkpoint copies matched the live project's files byte-for-byte at inspection. Local username and account-name occurrences were replaced in the distributed JSON; its different hash is expected. The original private files were read only.

Saved Requirement completion and saved Pipeline IR do **not** prove completed Model/Compiler/Run stages, a new engine, a benchmark, inference or genuine factory metadata. Those later artifacts remain pending. The actual IR GUI screenshot is also pending; no screenshot was constructed from these JSON files.
