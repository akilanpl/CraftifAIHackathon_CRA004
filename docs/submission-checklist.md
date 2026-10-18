# Submission checklist

User-provided event: Embedded SF × CraftifAI Physical AI Hackathon, Track A — PipeGen (Perception). User-provided deadline: October 18, 2026, 6:00 PM IST. Organizer requirements have not been independently verified in this repository.

## Application review

- [ ] Backend tests pass; record command and result.
- [ ] Frontend type-check and production build pass.
- [ ] API and WebSocket flow exercised from ingestion to dashboard.
- [ ] Zone create/edit/delete, incident filters/details and acknowledgment verified.
- [ ] Synthetic mode is clearly visible and its database stays separate.
- [ ] Live mode starts empty and reports unavailable telemetry honestly.
- [ ] Source contains no credentials or local incident databases.

## Required genuine PipeGen evidence — replay integration milestone

- [ ] Requirement stage completed.
- [ ] Actual Pipeline IR screenshot retained.
- [ ] Model selected/exported as ONNX with provenance.
- [ ] Compiler produced an NVIDIA TensorRT engine and actual speed report.
- [ ] Run stage executes live DeepStream on the GPU.
- [x] Genuine metadata mapped and adapter tests added.
- [x] Real detections produce persisted computed alerts, with initial-inside observations distinguished from observed entries.
- [x] Replay hold suppression and observed exits verified; exit/reentry logic unit-tested.
- [ ] Capture a genuine same-track observed reentry (this clip has zero).
- [ ] PipeGen export included or accessible from the repository.
- [ ] Real prototype evidence links source video, metadata and incident.

## Repository delivery

- [x] README describes real recorded replay and remaining live/evidence limitations.
- [ ] Setup works from a clean clone with pinned dependency files.
- [ ] Evidence locations are documented; no synthetic artifact represented as real.
- [ ] Source repository URL and project description submitted using the actual organizer workflow.

No boxes are automatically checked by documentation generation. Consult the final QA report for checks actually executed in this environment.

## Explicit seven-stage evidence status

| PipeGen-dependent stage | Status |
| --- | --- |
| Requirement | PENDING |
| Actual Pipeline IR | PENDING |
| Selected model/version | PARTIAL — YOLOv8m, semantic version unreported |
| Genuine TensorRT FP16 report | PARTIAL — selected actual report facts |
| Actual DeepStream execution | PARTIAL — real output audited; run screenshot/log not packaged |
| Genuine metadata | VERIFIED |
| Real-mode dashboard evidence | VERIFIED HISTORICAL REPLAY — synchronized street video |

See `../evidence/checklist.json` for the structured ledger. Historical synthetic screenshots remain application QA only; the real replay capture is separately labeled. Local source handoff and exact launch commands are in `github-readiness.md`. The configured GitHub repository is private; code updates use the existing authorized origin.

## Factory release acceptance gate

All checks below apply to the **new factory dataset**, not the historical street baseline:

- [x] Licensed warehouse video decoded and dimension/FPS/PTS checked; matching new inference remains pending.
- [ ] Separate actual PipeGen Requirement → IR → Model → Compiler → Run evidence captured.
- [ ] Compatible FP16 engine reuse identified as reuse; any new benchmark documented with its actual conditions.
- [ ] Genuine factory metadata produced by that run and preserved unchanged.
- [ ] Factory manifest contains matching video/metadata hashes, source ID and dimensions.
- [ ] Timing offset/tolerance inspected from that source pair and visually checked.
- [ ] Factory floor ROI reviewed on the actual footage; valid polygons assigned to the manifest camera.
- [ ] Separate dataset-bound SQLite storage retains acknowledgments without mixing street incidents.
- [ ] Browser pause/seek/rate/resize verified; playback does not duplicate persisted history.
- [ ] Real factory screenshot and actionable incident linked to exact metadata timestamps.
- [ ] Factory export separately archived, hashed and reviewed; baseline export preserved.
- [ ] Reviewed labels and held-out evaluation supplied before claiming precision/recall/mAP.
- [ ] INT8/fine-tuning/Jetson results marked NOT TESTED unless actually executed and measured.
- [ ] Final source/tests/build and artifact manifest reviewed before private release upload.

Current gate status: **PENDING**, because genuine factory run metadata has not been supplied to this documentation pass. Historical street metadata/dashboard are verified separately. See `../evidence/release-artifact-manifest.json` and `factory-release.md`. Official PDF requirements remain unverified because the document was not located; this checklist follows the user's supplied requirements.
