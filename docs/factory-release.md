# Factory safety release — evidence and asset boundary

The `release/factory-safety` branch preserves the known-good street replay while preparing an explicitly separate factory/warehouse dataset. Historical footage remains labeled **historical street**. A candidate factory clip is not a completed factory AI run. Reusing street metadata against different footage is prohibited.

## Current evidence status

| Item | Status | Evidence / limitation |
| --- | --- | --- |
| Historical street replay | DONE | 1,029 frames; 7,688 person observations; 89 recurring raw IDs; 33 application-computed alerts: 23 first observed inside, 10 observed entries; 11 observed exits, zero verified reentries |
| Original source/export preservation | DONE for read-only audit and private draft asset | Existing metadata/archive unchanged; archived export uploaded privately with API digest matching local hash |
| Factory footage | VIDEO VERIFIED; INFERENCE PENDING | Licensed Pexels Tiger Lily warehouse clip, H264 1920×1080, 25 FPS, 254 decoded frames, 10.16 s; metadata is not yet available |
| New factory PipeGen execution and matching metadata | PENDING | A new run is mandatory for the new video |
| Factory scene ROI | PENDING | Must be placed on the actual validated floor view; do not reuse the street polygon blindly |
| Factory synchronized dashboard | PENDING | Requires paired hashes, matching dimensions/source, verified PTS mapping and new metadata |
| Labeled accuracy, fine-tuning and INT8 comparison | NOT TESTED | No reviewed held-out factory labels or matched measurements supplied to this release documentation |
| Jetson deployment | NOT DEPLOYED / NOT TESTED | RTX execution and modeled Orin estimates do not establish Jetson deployment |

The separate Chat 2 factory mission records footage provenance and CPU decode validation under its `outputs/factory-mission/`. That is external provenance, not factory inference evidence. Update this report only from actual run outputs.

## Profile contract

A configured dataset manifest binds one video to its own genuine metadata using SHA-256, source ID, source frame dimensions and explicitly verified PTS offset. Profile state is `PENDING`, `READY` or `INVALID`; missing/invalid factory assets must not fall back to historical street files. Databases default to `data/profiles/<manifest-id>.sqlite3` and are bound to dataset identity, so factory history and acknowledgments cannot silently mix with street history. `GET /api/profile`, `/api/status` and the replay timeline expose the selected profile state.

The backend profile interface uses `SENTINEL_DATASET_PROFILE=factory|historical_street` and `SENTINEL_PROFILE_PATH=/absolute/path/to/manifest.json`. A manifest uses version 1 and includes `id`, `name`, `description`, `scene_type`, `source_kind: "recorded_pipegen"`, `video_path`, `metadata_path`, both hashes, `frame_width`, `frame_height`, `source_id`, `camera_id`, `pts_offset_ns`, `pts_mapping_verified: true`, `pts_verification_note`, `model_name`, `precision` and optional `tolerance_ns`. A factory manifest also requires a nonempty `zones` array of valid zone inputs assigned to its `camera_id`; those polygons must be checked against the actual factory frame. Relative media paths resolve against the manifest directory. Do not set `pts_mapping_verified` merely to satisfy validation; inspect source timing first.

Do not create a completed factory manifest from the historical street fields. The historical 33,366,700 ns offset and 8,350,000 ns tolerance are evidence for that source pair only. The factory source FPS and timestamps must determine its own mapping and tolerance.

## Metrics: measured, modeled and absent

The existing inspected FP16 summary reports 52,730,564 engine bytes, 4.94176 ms measured GPU compute and 5.84506 ms measured end-to-end engine latency. The reciprocal of engine latency is approximately 171 engine inferences/second; this is not full DeepStream throughput. The summarized report does not identify the measured device. User-provided baseline context says RTX 2060 SUPER and approximately 129 W, but power remains unverified in the packaged report (`power_watts_verified: null`).

The Orin NX values, approximately 168.72 estimated FPS at a modeled 15 W profile, are **modeled estimates**, not measurements and not deployment evidence. No supported factory accuracy, fine-tuning improvement, INT8 speed/power advantage or Jetson result is claimed.

## Official requirements source

No official problem-statement PDF was located in the seven pasted-text attachments or the scoped local `.pipegen`, Downloads, Documents and external-workspace search. This checklist therefore follows the user's supplied requirements. The actual official PDF and submission portal criteria remain unverified until provided or located. No stand-in PDF was generated.

## Checks executed for this documentation pass

- Parsed the evidence ledger, archive audit and release manifest as JSON; all valid.
- Confirmed exactly seven new factory evidence stages remain PENDING while the historical ledger is preserved.
- Read-only archive integrity/path/link/credential-pattern screening completed as recorded in `../evidence/export-archive-audit.json`.
- Ran `.venv/bin/python scripts/validate_dataset_profile.py /nonexistent/factory-manifest.json --scene factory`: returned exit code **2**, state **PENDING**, `verified: false`, with no substituted street source. This validates the documented missing-manifest behavior only.
- No official PDF was found; no claims of PDF compliance or factory inference verification were added.

Application regression/build/browser checks are reported by the primary/frontend/backend agents separately; these documentation checks do not substitute for them.

## Current application release checks

Primary-runtime suite: **123 backend tests**, **17 frontend tests**, TypeScript and production build passed. Browser checks confirmed the factory profile shows PENDING and zero history with no historical fallback; the Model Performance page loads its genuine JSON evidence; legacy street video still plays with aligned SVG/video bounds and sub-microsecond sampled PTS difference. Factory visual correctness remains unverified until its matching metadata is supplied.

The reusable CPU-only timing verifier is `scripts/verify_video_timestamps.py VIDEO METADATA --report REPORT.json` (system Python with existing GStreamer). It compares every decoded frame dimension and timestamp; additionally check browser presented media time. It does not prove execution provenance or rerun inference. The backend replay verifier also checks restart recovery, acknowledgment persistence, repeated WebSocket reconnection, observed transitions and native ROI disagreements.
