# Project description

Hazard Zone Sentinel implements the **Workplace Safety Sentinel** use case for **Track A — PipeGen (Perception)**. It turns warehouse video into tracked person metadata and reviewable restricted-zone incidents.

CraftifAI PipeGen v0.5.1 is the core perception tool. The saved seven-node workflow reads warehouse MP4 video, preprocesses frames, runs YOLOv8m ONNX through a TensorRT 10.3.0 FP16 engine, postprocesses person detections, performs NVIDIA DeepStream/NvDCF tracking and restricted-zone analytics, and emits structured JSON. FastAPI consumes those records, evaluates application-managed zones and stores entry incidents in SQLite. WebSocket updates feed a React/TypeScript dashboard for monitoring, incident review, acknowledgment and analytics.

The genuine recorded warehouse output contains **254 frames, 522 per-frame person observations and six observed track IDs**. Application analysis produces **two entry incidents, including one re-entry**, with two observed exits and 43 suppressed continued-occupancy observations. Track IDs do not establish unique physical people. The moving-camera footage uses a normalized image-space demonstration region.

The existing PipeGen report records **199 compiled layers**, **5.28244 ms GPU compute**, **6.19475 ms engine execution latency** and **188.877 reported engine inferences/sec**. These are prior engine measurements, distinct from full-pipeline FPS or the new Mac test. [Original engine summary](../evidence/04-tensorrt-fp16/warehouse-engine-summary.json).

The eight-page operations dashboard and separate ONNX Runtime CPU camera/video monitor remain intact. Browser camera controls, prerecorded CPU video inference and simulated camera tests are described separately in the [project README](../README.md).

The new Mac validation replays the original metadata through the existing application over HTTP and WebSockets using ephemeral databases. It performs no GPU inference. Original-video synchronization was not retested without the matching MP4. A new NVIDIA hardware/venue run and the original PipeGen GUI evidence remain pending; no organizer acceptance or submission receipt is claimed.
