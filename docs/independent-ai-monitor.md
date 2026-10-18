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

A start/restart/replay action must create or explicitly resume its own session; it must not silently replay incidents into an old session. Seeking in an already-analyzed file is visualization rather than a second persistence pass unless the operator explicitly chooses a new analysis session. Acknowledgments belong to isolated incident records. Stop/disconnect releases browser tracks, decoding resources, in-flight work and session ownership; final browser/API cleanup checks passed.

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

The primary final dashboard serves V2 and AI Camera Monitor on frontend **5173**, preserving V2 backend 8003 and routing independent AI to backend 8005:

```bash
SENTINEL_API_TARGET=http://127.0.0.1:8003 SENTINEL_AI_TARGET=http://127.0.0.1:8005 ./scripts/start-frontend.sh --port 5173 --strictPort
```

Open **http://127.0.0.1:5173** and select **AI Camera Monitor**. Vite routes the more specific `/api/ai` and `/ws/ai` paths to the independent service; V2 routes retain their existing target. Browser simulation, genuine virtual-video processing, uploaded MP4 processing, simulated USB lifecycle, speed controls, mobile layout and V2 replay regression passed. Final automated checks passed; actual Git push/main-merge status is recorded by the primary agent.

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

## Host guard and release authorization

The earlier approximately 962 MiB root-space hold is resolved: the user supplied a successful host storage-guard result, **exit 0**, with approximately **1.4 GB root free and 39 GB external free**. The primary agent confirmed this host output. Continue to rerun the guard before future large writes/downloads; the required reserves remain 1 GiB root and 20 GiB external. No system/mount changes were made by this feature.

The user explicitly approved keeping the existing **PUBLIC** visibility and pushing the feature branch, and subsequently authorized merging main **only after all checks and V2 regression pass**. Authorization is not evidence that a merge/push occurred; the primary agent records final commit, push and merge status. Physical USB hardware and independent quality metrics remain **NOT TESTED**.


## Current isolated demonstration and reproducible check

The primary dashboard is **http://127.0.0.1:5173/** → **AI Camera Monitor**, with independent backend **8005** and V2 backend **8003**. The alternate test frontend **http://127.0.0.1:5177/** remains available; its exact opt-in USB harness URL is **http://127.0.0.1:5177/?cameraTest=1**. The following alternate-port launch keeps the primary frontend available. To launch on a host after the storage guard passes, in separate terminals from the repository root:

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

## Simulated USB browser pathway — verified genuine inference and cleanup

The localhost Vite development test harness is enabled with **`?cameraTest=1`**; it is disabled by default in production. On the isolated demonstration open **http://127.0.0.1:5177/?cameraTest=1**, choose AI Camera Monitor → USB Camera and use the visible test-device controls. This is an application-owned MediaDevices abstraction; it does not override global `navigator.mediaDevices`.

The supplied stream is the real prerecorded warehouse video through `HTMLVideoElement.captureStream()`, using the same USB-frame capture and independent ONNX pathway. Source and detection provenance are separate: `capture_origin: "simulated_usb_camera"`, `input_is_simulated: true`, while real pixel/model processing has `provenance: "independent_ai_inference"`. The origin is **client-declared**, not server-attested; a source label cannot prove physical hardware identity. Session name visibly says SIMULATED USB CAMERA. This is neither a synthetic detection fixture nor a physical USB-camera test.

Actual browser checks passed discovery of two selectable test devices A/B, simulated permission grant/denial, unavailable-device handling, disconnect/reconnect, genuine CPU detection of three visible workers and acknowledgment. `../evidence/independent-ai/simulated-usb-genuine-inference.png` and `simulated-usb-unavailable.png` retain the browser evidence. The real captured/processed result displayed boxes on the workers.

`simulated-usb-real-stream.json` records **12 sampled actual WebSocket frame messages** with person counts **[3,3,3,3,3,2,2,0,0,0,3,3]** and approximately **649–866 ms** processing. The video loops to sustain the mock camera stream. Observations and incident totals across loops are **not unique people counts or reliable physical reentry evidence**; looping and approximate IoU identities affect transitions. Physical hardware always remains NOT TESTED.

The disconnect lifecycle defect was fixed and a fresh browser/API rerun confirmed **backend STOPPED, zero active streams, zero live tracks and a free inference worker**. Reconnecting test devices A/B resumed real frame inference. `simulated-usb-release.png` retains cleanup evidence. An earlier unexpected service SIGTERM had no Python exception; the dashboard stopped sampling, displayed error and reconnected after restart. The replacement service remained stable for more than seven minutes during final checks; this short observation is not a long-term reliability guarantee and the original SIGTERM cause remains unknown.

## CPU resource and final test checkpoints

`../evidence/independent-ai/cpu-runtime-validation.json` records a separate genuine six-frame CPU sample: **12 person observations**, two configured intra-op threads, approximately **1.99 average CPU cores** and **399.5 MiB peak process RSS**. The source is original warehouse JPEG pixels, without metadata inference input. This is a small process-resource sample, not camera/GPU/full-pipeline performance or a universal deployment bound.

Final combined checks passed **161 backend tests**, including **three actual-model live HTTP/WebSocket source integration tests with no skips**, **35 frontend tests**, TypeScript and production build. Final browser reload had zero unexpected console errors.

A real pointer-drawn rectangle from normalized `[0.4,0.35]` to `[0.9,0.9]` persisted in a new independent session; its fixture run returned 2 entries, 2 exits and 1 reentry. The final uploaded-video session produced three genuine worker detections. `final-upload-browser.png` and `final-mobile-browser.png` retain final upload and 390×844 browser checks. These session rules never replace the V2 polygon.

`../evidence/independent-ai/restart-isolation-verification.json` reports PASS: a live service restart retained the earlier real acknowledgment, and later real-session SQLite snapshot recovery preserved incident counts and acknowledgment states across the recorded sessions. Recovered sessions are stopped. Warehouse V2 play/pause and its two original incidents remained unchanged.

**Functional acceptance: PASS for independent real-video inference, simulation, browser upload, simulated USB pathway, lifecycle/cleanup, persistence, source isolation and V2 regression.** Physical USB camera hardware and independent accuracy metrics remain NOT TESTED. Public push/main merge are authorized subject to these checks; only the primary agent's final Git report establishes actual completion. No further feature-code changes are required by this documentation pass.


Final V2 check: the primary frontend process on 5173 was restored with V2 target 8003 and independent AI target 8005; backend data remained unchanged. A fresh browser verified source hash, play/pause, the two original incidents and zero console errors. `../evidence/independent-ai/final-v2-5173.png` records this final primary-dashboard check. All functional/browser release checks are complete; actual commit/push/merge remains the primary agent's final step.
