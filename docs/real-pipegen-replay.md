# Real PipeGen replay

The existing dashboard now accepts the observed PipeGen `video_json_export` batch through `backend.replay.load_export`. It uses genuine recorded detections. **REAL PIPEGEN REPLAY is neither live inference nor synthetic testing.** Synchronized original-video playback is now implemented and browser-verified; see [video replay](synchronized-video-replay.md). The metadata-only fallback and optional event-analysis session remain separate.

## Start

From the repository root, using an existing actual PipeGen export:

```bash
bash scripts/start-real-replay.sh /absolute/path/to/actual/metadata.json
```

In another terminal:

```bash
bash scripts/start-frontend.sh
```

Open `http://127.0.0.1:5173`. In the **REAL PIPEGEN REPLAY** controls choose speed, then Start replay. Pause/Resume and Stop are available. Starting again creates a distinct session; each session's computed incidents persist separately. Persisted totals include previous sessions, while session incident counts describe the current session. The default replay SQLite file is `data/pipegen-replay.sqlite3`, separate from live/synthetic databases. It is ignored by Git.

`SENTINEL_REPLAY_CAMERA` defaults to `cam-01`. `SENTINEL_REPLAY_PATH` can supply the input instead of a positional argument. No models, video, metadata originals, databases or credentials need to be committed. This path is read-only input; replay never writes back to the source export.

## Exact adapter semantics

- The export is one JSON object with a `frames` array, not JSONL. Full batch validation precedes replay state changes.
- Person observations require consistent `class_id: 0` and `label: person`. Other classes are excluded from person boxes. Contradictory labels/classes fail validation.
- Boxes are the original full-frame pixel `left/top/width/height`, converted by the stated width/height to normalized `[left/W, top/H, (left+width)/W, (top+height)/H]`. No guessed resizing, padding, clipping or axis swap is applied. Invalid fields, nonfinite numbers and out-of-frame geometry reject the export.
- Recognized candidate tracker IDs are scoped by replay session and source. The original ID remains available in replay annotations. Unknown/missing/sentinel IDs cannot create deduplicated person-entry incidents. An observed ID is not a verified physical identity.
- Original `pts_ns` is a relative video clock. Replay pacing uses its differences; it is never interpreted as Unix time. Canonical timestamps use an actual replay-session UTC start plus video elapsed time and are explicitly marked `timestamp_basis: replay_session_clock`. They are virtual replay timeline values, **not original capture timestamps**.
- No native entry/exit/event IDs are fabricated. Analytics component `unique_id: 17` is not an incident ID; `roi_counts` describes occupancy. Incident IDs are assigned by Sentinel to its own computed events.
- The geometry engine evaluates the bottom-center of the exported person box. Once inside, repeated frames do not create repeated incidents. Missing observations do not prove exit; replay retains occupancy until a confident observed outside position or a session reset. An explicit observed outside followed by inside can generate a new computed incident.
- Each new replay session resets engine state and namespaces tracking. Replay mode rejects live/synthetic ingestion endpoints so sources cannot mix silently. Live/synthetic behavior remains available in their existing modes.

## Initial polygon and comparison with native analytics

A new replay database seeds the actual configured PipeGen `restricted_zone` polygon: pixel `(1056,486), (1824,486), (1824,1026), (1056,1026)` in a 1920×1080 frame, or normalized `(.55,.45), (.95,.45), (.95,.95), (.55,.95)`. Confidence threshold is 0.5 and debounce is one observed frame. Users can edit the zone; incident results then describe that edited polygon, not the original native analytics configuration. Existing zones are never overwritten by startup.

Full-file audit: 1,029 frames; 7,688 person observations; 89 distinct observed person IDs; first PTS 33,366,700 ns; last 17,183,850,517 ns. These are observations/tracks, not 89 proven physical people or intrusion incidents. Native ROI occupancy is positive on 1,023 frames, peaks at five, and totals 2,461 person-in-ROI observations. Native per-object ROI tags and per-frame ROI counts agree throughout.

Bottom-center recomputation disagrees with native ROI membership on 52 frames/52 objects, with maximum count difference one. Applying confidence >=0.5 does not change that result. The exports round boxes to one decimal, but the largest disagreement lies 17.2 pixels from an ROI edge, so rounding alone is not an adequate explanation. Native class-count summaries also differ from exported object-list cardinality; do not substitute those summaries for observed detections. These discrepancies remain visible evidence, not values forced to agree by the adapter.

The recording does not establish a staged physical exit/reentry by a ground-truthed person. Computed box transitions, tracker gaps and native occupancy must not be promoted to real-world identity/safety accuracy claims.

## Benchmark provenance

Observed compiler artifacts identify YOLOv8m ONNX, TensorRT 10.3.0, FP16, 184 layers and a 52,730,564-byte engine. The engine report records end-to-end engine benchmark 5.84506 ms (approximately 171 FPS), with GPU compute 4.94176 ms. This is not full DeepStream pipeline throughput. A separate part of that report models a Jetson Orin NX; those modeled hardware/power/thermal estimates are not RTX measurements. The exported metadata contains no power telemetry, so the replay dashboard does not display 129 W as a verified measurement.

## Evidence and limitations

The original metadata is preserved externally. Its SHA-256 is `ae10cfba371d2d553f4804058240e56ade5653c83c86916f354892c55df6d941` (3,086,411 bytes). A small genuine frame excerpt and aggregate audit are versioned under `evidence/06-real-metadata/`; the full file remains local. The original export contains no capture UTC anchor; live ingestion still needs a verified upstream clock conversion. Replay counts must always be qualified by polygon, confidence/debounce settings and session.


## Verified single-session results

For the seeded original polygon, 1,029 actual frames produced 33 computed alerts: **23 first-observed-inside alerts and 10 observed outside-to-inside transitions**. There were 2,458 subsequent inside observations without duplicate alerts, 11 observed exits, and **zero observed reentries**. A vanished ID does not count as exit; all 33 alerts involve distinct candidate tracks in this clip. Replay final visible occupancy is three. API/WebSocket/SQLite and acknowledgment persistence are verified; see `evidence/06-real-metadata/replay-verification.json`. Reentry logic is covered by explicit unit tests, not falsely claimed as an event in this recording.
