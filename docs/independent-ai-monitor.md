# Independent AI Camera Monitor

This optional feature is developed on `feature/independent-ai-camera`, separately from Warehouse V2's known-good PipeGen replay. It must not open, rebuild, execute or modify PipeGen or replace its existing media, metadata, two incidents, export or release. It must not merge into main until independent real-model and regression acceptance checks succeed.

## Evidence status

| Capability | Current evidence | Claim permitted |
| --- | --- | --- |
| Original Warehouse V2 | Browser play/pause passed; original two incidents preserved | Existing recorded PipeGen evidence remains separate |
| Synthetic fixture scenario | Browser scenario completed: 2 entries, 2 exits, 1 reentry; acknowledgment passed | SIMULATED TEST DATA; not YOLO or camera evidence |
| Independent real video inference | Reproducible 26-frame genuine CPU stream, 52 person observations, acknowledgment verified; virtual-video browser passed | Real inference verified for this sample; model and approximate tracker remain imperfect |
| USB browser capture support | User-initiated capture implemented; five new frontend helper tests passed with API/permission/backpressure/upload coverage | PHYSICAL CAMERA HARDWARE TEST: NOT TESTED |
| Uploaded-video analysis | Genuine browser MP4 processing passed through the same independent worker | New isolated source/session; no reuse of V2 metadata |
| Independent real-person annotation/evaluation | NOT TESTED | Predictions must not become independent ground truth |

Update the new `../evidence/independent-ai/simulation-checklist.json` from executed checks only. Do not alter the Warehouse V2 evidence ledger to record these tests.

## Feasibility and storage gate

Host setup has now passed and is independently configured under `/mnt/seagate4/PipeGenHackathon/independent-ai-monitor`. ONNX Runtime **1.31.0**, **CPUExecutionProvider**, loads the existing YOLOv8m ONNX copied to the application-owned `models/` directory. The model SHA-256 is `8db1e3bb5e53410eb79da1e166fa3e1a05d6d1ff29df33af7345f2f3b73e20d7`; input is `[1,3,480,640]`. External `setup-provenance.json` reports the original unchanged. Dependencies and the model are external; host-launched sessions default to external storage. Sandbox QA used only small isolated session databases under the task workspace because the external mount is read-only there. No PipeGen launch or engine alteration is needed.

Initial sandbox inspection could not complete the storage guard's write probe and runtime packages were missing. That initial blocker is superseded by the primary agent's verified host setup. Continue running the user-required guard before further dependency copies or large inputs:

```bash
/usr/local/libexec/pipegen-user-storage-check && df -h / /mnt/pipegen-storage
```

Root must retain at least 1 GiB and external storage at least 20 GiB. The launcher selects external `models/yolov8m.onnx`, `dependencies/` and `sessions/` under `SENTINEL_AI_HOME` (default the external directory above). Explicit `SENTINEL_AI_MODEL_PATH`, `SENTINEL_AI_DEPENDENCIES_PATH` and `SENTINEL_AI_DATA_DIR` override those locations. Do not use old PipeGen detection JSON as independent model output.

## Source-agnostic processing contract

The intended worker path is real video/camera frames → independently loaded model → actual person detections → optional verified tracker → normalized zone logic → isolated SQLite incidents/WebSocket updates → video overlay. Virtual video, upload and browser camera should share the same worker protocol wherever feasible.

Simulation fixtures may provide known boxes to test the same event engine, but must carry explicit simulated provenance and never appear as independent model results. Track IDs supplied by simulation are expected fixture identity. Real tracker output is association, not proof of real-world identity; if tracking is unavailable, do not invent stable IDs.

Correlate each result with source ID, session ID, frame sequence and source/media timestamp. Match overlay to the displayed frame, discard stale responses and bound in-flight work; a slow worker must drop/defer capture instead of accumulating unlimited lag. Timestamp, confidence, dimensions and bbox values must be validated. FPS/latency appear only when measured from actual work, with their measured scope stated.

A start/restart/replay action must create or explicitly resume its own session; it must not silently replay incidents into an old session. Seeking in an already-analyzed file is visualization rather than a second persistence pass unless the operator explicitly chooses a new analysis session. Acknowledgments belong to isolated incident records. Stop/disconnect must release browser tracks, decoding resources, in-flight work and session ownership.

## Required release report

Record the actual engine/provider, model SHA-256, input video SHA-256/license, independent source/session IDs, source frame timestamps, actual inference latency/FPS, inference count, genuine detections and tracker limitations. Supply browser screenshots showing true person/box alignment at several points. Keep simulation expected-versus-observed results separate.

Report exact automated checks, browser failures, source-isolation checks, hardware NOT TESTED status, commit SHA and tree status. Real video inference is a required acceptance gate; mocked detections or an implemented adapter alone cannot satisfy it. Camera hardware is unavailable, so only its error/permission lifecycle can be tested automatically until the manual acceptance procedure is performed.

## Implemented local service and API

Start the isolated service from the repository root:

```bash
./scripts/start-ai-monitor.sh
```

It runs `backend.monitor_main:app` on port **8004**. This is separate from the Warehouse V2 backend. Inspect `http://127.0.0.1:8004/api/ai/status` before claiming runtime readiness. Session files default to `data/ai-monitor/<new-session-UUID>/` with a new SQLite database and configuration; `SENTINEL_AI_DATA_DIR` can explicitly select approved storage. No V2 database is opened by this service. Keep its storage lightweight and preserve the required free-space reserves.

| Interface | Purpose |
| --- | --- |
| `GET /api/ai/status` | Real inference availability and honest hardware status |
| `GET/POST /api/ai/sessions` | List/create isolated simulation, virtual_video, uploaded_video or usb_camera session |
| `GET /api/ai/sessions/{id}` | Session state |
| `POST /api/ai/sessions/{id}/frames?seq=N&media_time=S` | Raw JPEG frame; maximum 2 MiB; validated sequence/time |
| `PUT /api/ai/sessions/{id}/zone` | Change zone configuration |
| `POST /api/ai/sessions/{id}/pause`, `/resume`, `/stop` | Explicit session lifecycle |
| `POST /api/ai/sessions/{id}/simulation/step` | Explicit deterministic fixture, optional sequence body |
| `GET /api/ai/sessions/{id}/incidents` | This session's incidents |
| `PATCH /api/ai/incidents/{id}/acknowledge` | This independent incident's acknowledgment |
| `WS /ws/ai/{id}` | Independent session results/events |

Create a session with `source_type`, `name`, normalized `polygon` and optional `confidence_threshold`. Repeated sequences return the cached result instead of creating another event. A new sequence with backwards media time is rejected (409); seek/reanalysis requires a new session instead of silently replaying incident history. The worker allows one global in-flight inference request, rejects concurrent work with 429 and has no unbounded queue. Real association uses an experimental IoU tracker; its IDs are estimates, not verified identity through occlusion.

The independent detector reads `SENTINEL_AI_MODEL_PATH` and optionally `SENTINEL_AI_DEPENDENCIES_PATH`. The installed ONNX Runtime CPU provider has loaded the model and produced genuine detections in the real-frame checks below.

## Frontend source behavior

Choose **AI Camera Monitor** in navigation. Options are Simulation, Warehouse virtual video, Uploaded MP4 and USB Camera. The virtual source reads real existing video frames from the established video endpoint, never the old metadata as independent inference. Uploaded MP4 stays in the browser as a blob URL (250 MiB selection limit); only sampled JPEG frames are transmitted. No original MP4 upload/storage is needed for this path. A future server-side upload option remains disabled unless approved off-root storage is configured and checked.

The source preview intentionally has no detection overlay. The authoritative processed-frame display pairs the captured JPEG with its returned sequence, media time and session identity, preventing stale boxes over a newer source frame. Only one browser frame is in flight. Stop invalidates pending responses and stops USB media tracks while retaining the selected browser MP4 and frozen last processed frame for inspection/restart. Source change or module unmount also revokes upload/processed-frame blob URLs. USB permission requires the explicit Connect camera action, then Start monitoring. Real monitoring is disabled while the real inference service is unavailable. Simulation always displays SIMULATED TEST DATA.

## Deterministic expected result

The implemented fixture sequence is empty → outside → inside → hold → hold → outside → reentry → hold → outside. Its expected result is **2 entries, 2 exits, 1 reentry and 0 duplicate hold alerts**. The actual browser run matched **2 entries, 2 exits and 1 reentry** and acknowledgment passed; see `../evidence/independent-ai/simulation-browser.png`. The hold sequence produced no repeated entry alerts. This validates simulated business logic, not YOLO recognition; genuine real-frame checks and physical hardware remain separate.

## Frontend launch and capture-rate distinction

Keep the V2 backend on its established port 8003, start the independent service on 8004, then run the existing frontend in another terminal:

```bash
SENTINEL_API_TARGET=http://127.0.0.1:8003 SENTINEL_AI_TARGET=http://127.0.0.1:8004 ./scripts/start-frontend.sh --port 5173 --strictPort
```

Open **http://127.0.0.1:5173** and select **AI Camera Monitor**. Vite routes the more specific `/api/ai` and `/ws/ai` paths to the independent service; V2 routes retain their existing target. Browser simulation, genuine virtual-video processing, uploaded MP4 processing, lifecycle/speed controls, mobile layout and V2 replay regression have passed. Final automated regressions and operational release holds are recorded below.

Capture resizes the longest image edge to at most 960 pixels and samples at a ceiling of 3 FPS. That capture ceiling is a client scheduling limit, **not measured detector throughput**. The processed frame records its own dimensions; normalized overlays must use those dimensions/viewport consistently. Actual inference latency/FPS must be measured by the real worker and recorded separately.

## Executed independent real-frame validation

The primary agent decoded actual source-video frames **0, 38, 66, 125, 200 and 253** and processed their visual pixels through the independent ONNX worker at confidence threshold **0.5**. Detection counts were **3, 3, 3, 3, 0 and 0**. Boxes around workers were visually checked in the first four sampled frames; the final two sampled views were empty. No previous PipeGen metadata supplied these independent detections.

Observed per-frame processing was approximately **630–871 ms**, including JPEG handling, preprocessing, inference and postprocessing. These six small samples are **not a benchmark**, not model-only inference latency and not full-video measured throughput. A 3 FPS client sampling ceiling is not an achieved FPS claim. Physical USB hardware and independently labeled mAP/precision/recall remain **NOT TESTED**.

The earlier tracker-expiry issue was repaired and the genuine stream/browser checks were rerun. The completed stream report below supersedes that pending rerun; experimental IoU identity limitations remain.

The final regression run passed **152 backend tests, 30 frontend tests, TypeScript and the production build**, with the external real model configured (no skipped inference compatibility check). The only backend warning is an upstream Starlette/AnyIO deprecation. Browser simulation, virtual video, genuine browser upload and V2 replay checks are verified; physical camera hardware remains NOT TESTED.

## Completed reproducible genuine stream and browser checks

`../evidence/independent-ai/genuine-api-stream.json` records the actual run produced by `scripts/verify-independent-video.py`: **26 sampled real frames, 52 person observations, 2 persisted incidents and 1 observed exit**. The two incidents are **one first-observed-inside record and one observed reentry**; these are not two newly observed boundary crossings. Acknowledgment was verified. This is independent ONNX processing of real pixels, not prior PipeGen metadata. Approximate tracker identities are explicitly marked `experimental_iou_association`.

Measured CPU JPEG decode/preprocess/ONNX/postprocess latency: **median 675.50 ms, minimum 629.44 ms, maximum 858.28 ms**. The reciprocal of the median is about **1.48 processed frames/s** for this sample and scope. It is not live-camera FPS, an end-to-end pipeline benchmark, a GPU/TensorRT comparison or a claim that the 3 FPS capture ceiling was achieved.

The primary agent verified genuine virtual video and browser-selected upload, pause/resume, backward-seek rejection (409; create a new session), restart after playback end, 0.5×/2× playback speeds and mobile 390×844 layout. Browser console contained zero errors/warnings during those checks. Warehouse V2 still played/paused and retained its two original incidents. Screenshots: `genuine-virtual-camera-browser.png`, `genuine-upload-browser.png`, `mobile-browser.png` and `v2-regression-browser.png` under the new independent evidence directory.

**Known false positive:** browser inspection observed shelving classified as a person near media time **4.24 s**, confidence about **0.54**. The model is imperfect; detector confidence is not correctness. IoU IDs are approximate associations and do not establish physical identity across occlusion, motion or missed detections. No independent labeled accuracy, mAP, precision or recall is claimed. The moving-camera stock video and configurable image polygon do not validate a real factory safety system.

## Operational release holds

Root free space unexpectedly dropped to approximately **962 MiB**, below the required 1 GiB reserve. The agent's download cache was cleared and the user was asked to free at least 250 MiB on the host. Do not start new downloads, large writes or experiments until the storage guard passes again; external session storage does not waive the root reserve.

The user explicitly approved keeping the existing **PUBLIC** visibility and pushing only the feature branch. Main stays at `14b787201de81263a4ebf1e393f406e7a57266a0`; this feature is not merged. Physical USB hardware test and independent quality metrics remain **NOT TESTED**. Storage reserve remains an operational hold until the host reports sufficient free space.


## Current isolated demonstration and reproducible check

The verified running feature demonstration is **http://127.0.0.1:5177/** → **AI Camera Monitor**, using independent backend **8005** and the existing V2 backend **8003**. V2 stays on **http://127.0.0.1:5173/**. To launch on a host after the storage guard passes, in separate terminals from the repository root:

```bash
AI_PORT=8005 ./scripts/start-ai-monitor.sh
```

```bash
SENTINEL_API_TARGET=http://127.0.0.1:8003 SENTINEL_AI_TARGET=http://127.0.0.1:8005 ./scripts/start-frontend.sh --port 5177 --strictPort
```

If either port is already occupied by the working instance, use that instance instead of starting a duplicate. The sandbox QA instance explicitly overrides only `SENTINEL_AI_DATA_DIR` to a small workspace QA directory; the host launcher defaults to external sessions. An older unconfigured service may occupy 8004; it is not the verified worker. Stop only that optional AI service with Ctrl+C in its owning terminal before reusing 8004. Do not stop V2.

Linux Mint's existing system PyGObject/GStreamer can reproduce real H.264 MP4 inference without new media dependencies:

```bash
/usr/bin/python3 scripts/verify-independent-video.py \
  --video /path/to/warehouse-workers-4281405-1080p.mp4 \
  --api http://127.0.0.1:8005/api/ai \
  --output /path/on/external/storage/independent-verification.json
```

The clip is the original attributed warehouse source in the V2 manifest/README; no video or model binary is added to Git. The normalized verification polygon is an independent session rule and never replaces the V2 polygon. The utility samples every tenth source frame, acknowledges one resulting incident when present, stops its own session and writes its report.
