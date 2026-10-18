# Factory safety release — evidence and asset boundary

The `release/factory-safety` branch preserves the known-good street replay while preparing an explicitly separate factory/warehouse dataset. Historical footage remains labeled **historical street**. The completed factory output is now preserved as an immutable metadata snapshot; live GUI execution evidence and downstream visual QA remain distinct checks. Reusing street metadata against different footage is prohibited.

## Current evidence status

| Item | Status | Evidence / limitation |
| --- | --- | --- |
| Historical street replay | DONE | 1,029 frames; 7,688 person observations; 89 recurring raw IDs; 33 application-computed alerts: 23 first observed inside, 10 observed entries; 11 observed exits, zero verified reentries |
| Original source/export preservation | DONE for read-only audit and private draft asset | Existing metadata/archive unchanged; archived export uploaded privately with API digest matching local hash |
| Factory footage | VERIFIED SOURCE | Licensed Pexels Tiger Lily warehouse clip, H264 1920×1080, 25 FPS, 254 decoded frames, 10.16 s; its matched factory metadata snapshot is preserved |
| New factory PipeGen output | VERIFIED METADATA SOURCE; LIVE-DEMO EVIDENCE STILL REQUIRED | Separate project output: 254 frames, 522 person observations, 6 raw tracker IDs; generated pipeline uses the warehouse source. Actual venue demonstration/run capture remains outstanding |
| Factory scene ROI | CONFIGURATION VERIFIED; PHYSICAL VALIDITY LIMITED | Final frame-relative polygon `(0.42,0.74)`–`(0.62,0.86)`; generated native `RestrictedZone` pixel coordinates `(806,799),(1190,799),(1190,929),(806,929)`. Camera moves; hypothetical screen zone, not calibrated physical hazard |
| Factory synchronized dashboard | VERIFIED RECORDED REPLAY | Browser frames 25/50/75/100 at 1/2/3/4 s aligned with original pixel boxes and SVG rectangles; sampled PTS delta zero. App screenshot preserved; this is not PipeGen GUI or live inference evidence |
| Labeled accuracy, fine-tuning and INT8 comparison | NOT TESTED | No reviewed held-out factory labels or matched measurements supplied to this release documentation |
| Jetson deployment | NOT DEPLOYED / NOT TESTED | RTX execution and modeled Orin estimates do not establish Jetson deployment |

The separate Chat 2 factory mission records footage provenance and CPU decode validation under its `outputs/factory-mission/`. The separate completed metadata snapshot now supplies genuine factory observations; provenance research alone would not have supplied them.

## Profile contract

A configured dataset manifest binds one video to its own genuine metadata using SHA-256, source ID, source frame dimensions and explicitly verified PTS offset. Profile state is `PENDING`, `READY` or `INVALID`; missing/invalid factory assets must not fall back to historical street files. Databases default to `data/profiles/<manifest-id>.sqlite3` and are bound to dataset identity, so factory history and acknowledgments cannot silently mix with street history. `GET /api/profile`, `/api/status` and the replay timeline expose the selected profile state.

The backend profile interface uses `SENTINEL_DATASET_PROFILE=factory|historical_street` and `SENTINEL_PROFILE_PATH=/absolute/path/to/manifest.json`. A manifest uses version 1 and includes `id`, `name`, `description`, `scene_type`, `source_kind: "recorded_pipegen"`, `video_path`, `metadata_path`, both hashes, `frame_width`, `frame_height`, `source_id`, `camera_id`, `pts_offset_ns`, `pts_mapping_verified: true`, `pts_verification_note`, `model_name`, `precision` and optional `tolerance_ns`. A factory manifest also requires a nonempty `zones` array of valid zone inputs assigned to its `camera_id`; those polygons must be checked against the actual factory frame. Relative media paths resolve against the manifest directory. Do not set `pts_mapping_verified` merely to satisfy validation; inspect source timing first.

Do not create a completed factory manifest from the historical street fields. The historical 33,366,700 ns offset and 8,350,000 ns tolerance are evidence for that source pair only. The factory source FPS and timestamps must determine its own mapping and tolerance.

## Metrics: measured, modeled and absent

The existing inspected FP16 summary reports 52,730,564 engine bytes, 4.94176 ms measured GPU compute and 5.84506 ms measured end-to-end engine latency. The reciprocal of engine latency is approximately 171 engine inferences/second; this is not full DeepStream throughput. The summarized report does not identify the measured device. User-provided baseline context says RTX 2060 SUPER and approximately 129 W, but power remains unverified in the packaged report (`power_watts_verified: null`).

The Orin NX values, approximately 168.72 estimated FPS at a modeled 15 W profile, are **modeled estimates**, not measurements and not deployment evidence. No supported factory accuracy, fine-tuning improvement, INT8 speed/power advantage or Jetson result is claimed.

## Official requirements source

The [official problem-statement PDF](../evidence/01-requirement-and-flow/official-problem-statement.pdf) has now been found and read in full: 7 pages, 142,647 bytes, SHA-256 `a1da48261c91d9668e15619b40f5c93e492f40814f0921c31c831db407862966`. It requires the full five-stage PipeGen flow, TensorRT engine with PipeGen speed report, GPU execution from an allowed source and actionable output (page 2). Deliverables are working hardware prototype (page 5), repository including export, project description and actual Pipeline IR/TensorRT-report screenshots (page 6). PipeGen must be essential to the product (pages 2 and 7).

INT8 or actual Jetson deployment with speed/power/accuracy trade-offs is an optional Track A bonus (pages 1–2). Custom factory labels/fine-tuning are user-requested additions, not mandatory Track A eligibility requirements. The official rules allow a video file as input; a replay dashboard is not a substitute for showing the actual pipeline running on hardware.

Page 6 prints 4:00 pm without a timezone. The user explicitly selected October 18, 2026, 4 PM IST as the cutoff, superseding earlier 6 PM instructions. The exact page-mapped checklist and PipeGen submission URL are in `submission-checklist.md`.

Factory status: **saved Requirement/IR, new FP16 engine report and genuine factory metadata are verified; profile READY; recorded browser replay and computed alert counts verified; PipeGen stage screenshots, export packaging and live venue demonstration remain outstanding**. This PDF review itself establishes no inference/accuracy result.

## Checks executed for this documentation pass

- Parsed the evidence ledger, archive audit and release manifest as JSON; all valid.
- Preserved the seven-stage factory ledger and historical ledger separately; updated each stage only as genuine artifacts became available.
- Read-only archive integrity/path/link/credential-pattern screening completed as recorded in `../evidence/export-archive-audit.json`.
- Ran `.venv/bin/python scripts/validate_dataset_profile.py /nonexistent/factory-manifest.json --scene factory`: returned exit code **2**, state **PENDING**, `verified: false`, with no substituted street source. This validates the documented missing-manifest behavior only.
- Read the complete official PDF using `pdftotext`; verified 7-page document metadata and SHA-256, and rendered/visually reviewed mandatory page 2 and submission/setup page 6. Updated the page-mapped checklist. No factory inference or overall compliance completion is claimed.

Application regression/build/browser checks are reported by the primary/frontend/backend agents separately; these documentation checks do not substitute for them.

## Current application release checks

Primary-runtime suite: **136 backend tests**, **25 frontend tests**, TypeScript and production build passed. Browser checks confirmed the factory profile shows PENDING and zero history with no historical fallback; the Model Performance page loads its genuine JSON evidence; legacy street video still plays with aligned SVG/video bounds and sub-microsecond sampled PTS difference. Those were the earlier pending-profile checks. Matching factory metadata and the subsequent real recorded-video browser QA are now verified below.

The reusable CPU-only timing verifier is `scripts/verify_video_timestamps.py VIDEO METADATA --report REPORT.json` (system Python with existing GStreamer). It compares every decoded frame dimension and timestamp; additionally check browser presented media time. It does not prove execution provenance or rerun inference. The backend replay verifier also checks restart recovery, acknowledgment persistence, repeated WebSocket reconnection, observed transitions and native ROI disagreements.


**Operative cutoff: October 18, 2026, 4 PM IST.** The user explicitly selected this cutoff after the PDF discrepancy was raised. Prior 6 PM assumptions are superseded.

## New Warehouse FP16 v2 checkpoint

Project `5b159399-c172-4ac5-8b45-430bd54a4a99` now has saved Requirement and PipelineIR evidence. Sanitized copies preserve the original hashes and requested YOLOv8m, NvDCF and final frame-relative zone `(0.42,0.74)`–`(0.62,0.86)`. This zone is hypothetical and the camera moves; it is not a calibrated fixed-world industrial safety boundary. Official IR graph screenshot remains pending.

The new model has a genuine newly built TensorRT10.3 FP16 engine: 52,792,260bytes,199layers, build16.304s. Its numeric report records5.28244msGPUcompute and6.19475msend-to-endengine timing. The measured device is unidentified in that report. Model semantic version, measured power, fullpipelineFPS, INT8, accuracy and Jetson deployment are unverified. See `../evidence/04-tensorrt-fp16/warehouse-engine-summary.json`; these facts supersede historical engine values only for the new model; engine timing is not full factory-pipeline throughput. Original reports/engine unchanged and externally stored.

## Preserved completed factory metadata snapshot

Use `../evidence/06-real-metadata/warehouse-fp16-v2-metadata.json` for verification. SHA-256: `b88db711a3daf13d494c8c438ad8f13b6f5aa262d9d7402e621be83439c9ccce`; 175,878 bytes; 254 frames; 522 person observations; 6 raw person tracker IDs; source 0, 1920×1080. Metadata PTS spans 80,000,000–10,200,000,000 ns. The primary agent decoded all 254 video frames and matched timestamps using +80,000,000 ns video-to-metadata mapping. Those are source/timing checks, not visual detection accuracy.

The original output path can be overwritten by subsequent operator runs; the immutable completed snapshot avoids partial-file reads and prevents changing replay evidence. No source JSON was repaired or detections generated by the application. Generated pipeline source and native pixel ROI were inspected separately by the primary agent.

Final running endpoints are backend `http://127.0.0.1:8003` and frontend **http://127.0.0.1:5173**. Actual browser QA checked frames 25/50/75/100 at 1/2/3/4 seconds: original pixel boxes and displayed SVG rectangles matched, with sampled PTS delta zero. `../evidence/07-real-mode-dashboard/warehouse-real-video-overlay.jpg` shows the genuine recorded warehouse video, person boxes and red zone. It is an application screenshot, not a PipeGen GUI graph/report or a capture proving inference was currently executing.

Verified factory analysis produces **2 observed-entry alerts, including 1 observed same-track reentry; 0 initial-inside alerts; 2 observed exits; 43 inside-hold observations suppressed**. Track 0 has entry frames 38 and 66. Restart checks preserved the two event IDs and acknowledgment states. Native ROI occupancy differs from application bottom-center box geometry in **9 frames**; the cause is unresolved and is not explained by rounding or confidence filtering. Do not treat native ROI counts as ground truth or silently hide disagreement. The moving camera makes this a hypothetical frame-relative zone, not a calibrated industrial hazard boundary. See `../evidence/06-real-metadata/factory-metadata-audit.json`.

Four raw IDs have 13 gap reappearances; those observations do not establish real-world identity or prove tracker ID reuse. No precision/recall/mAP is inferred from this analysis.

No new factory export archive was located under the scoped external exports/Chat 2 evidence directories during this pass. Historical private draft asset remains preserved; a new factory export and genuine IR/speed-report GUI screenshots are still required.


## Final verification boundary

Recorded factory playback, frame/overlay timing and two persisted incidents are verified. Actual PipeGen GUI IR/speed-report screenshots, a new factory export and the live hardware demonstration remain pending. The operative cutoff remains **October 18, 2026, 4 PM IST**. The primary agent is running the final regression suite; do not label anticipated test totals as completed until its results are recorded.


## Final export distribution

New factory export independently audited and uploaded to the private repository [warehouse release](https://github.com/akilanpl/hazard-zone-sentinel/releases/tag/warehouse-fp16-v2-2026-10-18). Remote134,818,189byte asset digest matches local SHA-256 `5a2314ab3b97787ec699bb185b767bbf4ab70b7517433988d8e6d9e0c3aa4dec`. New export availability is complete; judge access and official GUI screenshots remain submission gates. The source video stays external.
