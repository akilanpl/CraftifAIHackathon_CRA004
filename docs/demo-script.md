# Verified warehouse demonstration — 90 seconds

Use the real recorded warehouse profile at `http://127.0.0.1:5173/`. Do not run another analysis session during ordinary replay: the existing two alerts are persisted, and video controls intentionally do not write duplicates. A clean database needs one explicit metadata analysis first.

**0–15 seconds:** “Hazard Zone Sentinel turns genuine PipeGen person tracks into restricted-zone incidents. This warehouse video was processed by our five-stage PipeGen pipeline using YOLOv8m, TensorRT FP16, NvDCF tracking and NVIDIA analytics. The dashboard is clearly labeled recorded replay.”

**15–35 seconds:** “The actual video and metadata share verified hashes and timestamps. These boxes follow real workers, with original IDs and confidence. The red aisle polygon comes from the generated DeepStream configuration. The camera moves, so this is a hypothetical screen-relative demonstration rather than a calibrated factory safety deployment.”

**35–50 seconds:** “The 254-frame clip contains 522 person observations and 6 observed track IDs, not 6 verified people. Our bottom-center polygon analysis produces 2 entry alerts for track 0, including 1 re-entry, and 2 observed exits. Holding inside suppresses repeated alerts. Native occupancy differs on 9 frames; we report that disagreement.”

**50–65 seconds:** “Open Incident center to inspect the recorded PTS and original track, acknowledge an event, and filter history. FastAPI delivers WebSocket updates; SQLite keeps incidents and acknowledgments across restart. Video pause, seeking and replay keep the same stored count.”

**65–80 seconds:** “The new engine report shows 188.877 inferences/s, 6.19475 ms mean engine latency, and 135.222 W GPU-board power during the engine run. Those are PipeGen-reported engine measurements, not full-pipeline throughput or whole-machine power. INT8, independent accuracy and Jetson deployment are not tested.”

**80–90 seconds:** “The private source and matching PipeGen export are available separately. Show the actual Pipeline IR and speed-report screenshots and the GPU pipeline run for required hardware evidence. The application screenshot supports that demonstration; it does not replace it.”

## Operator evidence before submitting

Capture the actual PipeGen graph, TensorRT speed-report panel and execution evidence. Confirm judges can access the private repository/export, complete the actual project form, and keep its receipt before the **4 PM IST cutoff**. User reports feedback complete; final project-link/receipt still need confirmation.

---

# Historical synthetic rehearsal (preserved)

# Demonstration script

## Application-only rehearsal (SYNTHETIC TEST MODE)

1. Start backend with `SENTINEL_MODE=synthetic` and start the frontend as in setup.
2. Show the visible synthetic mode label. State: **These detections are synthetic application tests; this is not camera or PipeGen evidence.**
3. Open live monitoring. The display is a Detection Metadata View unless an actual video URL is configured. Explain the normalized red restricted polygon and tracked box.
4. Use synthetic step: outside produces no incident. Next step enters the zone and creates an incident. Holding inside produces no duplicate. Exit then re-entry permits a new incident.
5. Inspect the incident, acknowledge it, filter by zone or severity, and show that status updates without a page refresh.
6. Use zone management to create/edit a polygon and save. Explain validation of normalized coordinates and self-intersections.
7. Stop the synthetic backend and start live mode. Show separate incident storage and honest disconnected/unavailable source status.

Synthetic replay advances on user action; this is deterministic test input, not inference. Changing the seeded synthetic zone may change expected results. Use a fresh synthetic database only if an empty rehearsal is needed, retaining prior data if it matters.

## Genuine judging demonstration (requires external integration)

1. Show the actual PipeGen project stages and Pipeline IR screenshot.
2. Show the actual ONNX → TensorRT FP16 compile and speed report.
3. Start actual DeepStream camera/video inference on the NVIDIA GPU.
4. Run the configured native adapter and show metadata receipt in Sentinel.
5. With a real camera, stand outside the polygon; no incident. Enter; one incident. Hold position; no repeats. Exit and re-enter; another incident.
6. Match the source timestamp/camera/track to stored incident JSON and dashboard. Show acknowledgment and incident history.
7. Retain raw metadata, actual report, export and prototype evidence in the documented evidence locations.

Never substitute the synthetic rehearsal for the genuine pipeline demonstration. Missing GPU/FPS/latency information remains unavailable until real telemetry is supplied.

## 90-second narration for the current application rehearsal

**0–15 seconds:** “Hazard Zone Sentinel turns tracked person metadata into actionable workplace safety incidents. CraftifAI PipeGen is our required perception pipeline. Today this application rehearsal is explicitly in synthetic test mode; the genuine GPU pipeline evidence is still pending.”

**15–35 seconds:** “This is a Detection Metadata View. The red polygon is a configured restricted area. The person starts outside, so no incident is created. On entry, the backend checks the bottom-center of the bounding box against the polygon and generates an incident with camera, zone, track, confidence and provenance.”

**35–50 seconds:** “Keeping the same person inside does not spam alerts. Moving outside resets the tracked entry state, and re-entry produces a new incident. Missing identities are flagged rather than invented.”

**50–65 seconds:** “The dashboard receives updates through WebSocket. We can inspect and acknowledge this incident, filter history and inspect SQLite-backed trends. The synthetic database is separate from live operation.”

**65–80 seconds:** “Operators can edit zone vertices and severity, then save validated normalized coordinates. Missing video, FPS and inference telemetry remain clearly unavailable. No camera stream or benchmark is simulated as real evidence.”

**80–90 seconds:** “The remaining integration is to map genuine PipeGen metadata, retain the actual IR and TensorRT report, and record the live DeepStream entry-to-incident demonstration. The application is ready for that connection.”

## Factory release narration and fallback

Until genuine factory assets and a successful new run exist, introduce the screen as **factory dataset pending**. Demonstrate profile validation and separate storage, then explicitly switch to **historical street replay** if demonstrating the known-good application. Never call the street scene a factory or overlay street detections onto a factory video.

Once the factory profile is READY, verify the actual footage/boxes/ROI together before recording. State the real source, model and run; show entry/hold/exit only where actually observed. Describe first-seen-inside separately from an observed crossing. Do not promise reentry evidence when none exists. Retain the original street capture and its known 33-alert single-session analysis as historical fallback evidence.
