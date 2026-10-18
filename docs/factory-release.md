# Verified warehouse release

**Application:** http://127.0.0.1:5173/ · **API:** http://127.0.0.1:8003/ · **Cutoff:** October 18, 2026, **4 PM IST**, explicitly selected by the user.

## Verified results

The new Warehouse FP16 v2 project `5b159399-c172-4ac5-8b45-430bd54a4a99` produced genuine metadata matching its warehouse video. The recorded dashboard uses those detections; synthetic input and historical street data remain separate.

| Result | Verified value |
| --- | --- |
| Source frames / duration | 254 / 10.16 seconds |
| Frame dimensions / source | 1920×1080 / source 0 |
| Person observations / tracker IDs | 522 / 6; IDs do not establish unique physical people |
| Computed entry alerts | 2, including 1 observed same-track reentry |
| Observed exits / initially inside | 2 / 0 |
| Repeated inside observations suppressed | 43 |
| Native ROI disagreement | 9 frames; cause unresolved, not hidden or forced to agree |
| Current released application checks | 161 backend tests, 35 frontend tests, TypeScript and production build passed; includes independent module while preserving V2 |

The actual generated `RestrictedZone` polygon uses pixels `(806,799),(1190,799),(1190,929),(806,929)`. The application uses these exact coordinates normalized by 1920×1080. The camera moves and the zone is hypothetical and frame-relative; this is not a calibrated industrial safety deployment.

## Video, timestamps and persistence

- Video SHA-256: `14fb11cda9d031b497755195c04f6781df3a579d9044155114a3923cc5f43671`.
- Immutable metadata: [warehouse-fp16-v2-metadata.json](../evidence/06-real-metadata/warehouse-fp16-v2-metadata.json), 175,878 bytes; SHA-256 `b88db711a3daf13d494c8c438ad8f13b6f5aa262d9d7402e621be83439c9ccce`.
- Every decoded source-frame timestamp matched the export. Metadata PTS = presented video time + **80,000,000 ns**. Metadata PTS spans 80,000,000–10,200,000,000 ns.
- Actual browser frames 25, 50, 75 and 100 at media times 1, 2, 3 and 4 seconds were visually reviewed. Original pixel boxes and equal SVG/video rectangles matched; sampled timestamp differences were zero.
- [Real warehouse screenshot](../evidence/07-real-mode-dashboard/warehouse-real-video-overlay.jpg) and [alignment observations](../evidence/07-real-mode-dashboard/warehouse-browser-alignment.json) preserve the checks.
- HTTP/WebSocket delivery, independent SQLite reading, acknowledgment persistence, reconnects and restart recovery passed. Actual demo-service restart retained both incident IDs and acknowledgment states.
- Playback, pause, seek and replay do not append incidents. Explicit **Analyze new session** intentionally creates another persisted analysis session. A clean clone starts with empty history until analysis is requested.

The [metadata audit](../evidence/06-real-metadata/factory-metadata-audit.json) documents entry frames 38 and 66, exits and native occupancy disagreements. Missing tracks do not imply exits; gap reappearances do not prove identity reuse. No ground-truth accuracy is inferred from these checks.

## Model evidence and limits

The new YOLOv8m ONNX model compiled to a new TensorRT 10.3 FP16 engine: 52,792,260 bytes, 199 layers, 16.304-second build. Its semantic model version is not reported; the exact engine fingerprint is retained in the [selected summary](../evidence/04-tensorrt-fp16/warehouse-engine-summary.json).

PipeGen reports **188.877 engine inferences/s**, **5.28244 ms mean GPU compute** and **6.19475 ms mean end-to-end engine latency**. Engine throughput is reported separately, not inferred from latency. Its nested measurement reports **135.222 W GPU-board power during the engine run**, via `nvidia-smi`, 66 samples, reported accuracy ±5 W. This audit did not independently rerun those measurements. The reconciliation section leaves the measured device unidentified.

These are engine-scope results, not full DeepStream FPS or whole-system power. Orin NX estimates are modeled, not Jetson deployment evidence. INT8, independently labeled precision/recall/mAP and Jetson deployment remain **NOT TESTED**. The older 184-layer street engine and 33-alert street analysis remain historical only.

## Launch and source protection

```bash
./scripts/start-warehouse-demo.sh /absolute/path/to/warehouse-workers-4281405-1080p.mp4
```

Second terminal:

```bash
SENTINEL_API_TARGET=http://127.0.0.1:8003 ./scripts/start-frontend.sh --port 5173 --strictPort
```

The launcher binds the explicit video/metadata hashes, source, dimensions, verified offset and zone to a separate `data/profiles/warehouse-fp16-v2.sqlite3`. Missing or invalid factory assets never substitute street files. The original metadata, old database and baseline export were preserved. Safety tags retain `40d2975` and `22edb32`.

## Export and remaining submission gates

The actual new export is independently audited and uploaded as a [factory export prerelease asset](https://github.com/akilanpl/hazard-zone-sentinel/releases/tag/warehouse-fp16-v2-2026-10-18): **134,818,189 bytes**, SHA-256 `5a2314ab3b97787ec699bb185b767bbf4ab70b7517433988d8e6d9e0c3aa4dec`. GitHub's digest matches the unchanged local archive. The video stays external and its wrapper requires `--input`; the archive is outside ordinary Git history.

The [official seven-page PDF](../evidence/01-requirement-and-flow/official-problem-statement.pdf) requires the five-stage flow, TensorRT report, actual GPU execution and actionable output (page 2), a hardware demonstration (page 5), and source/export, description and actual IR/speed-report screenshots (page 6). Pitch/video and INT8/Jetson bonuses are optional. See the [page-mapped checklist](submission-checklist.md).

Remaining gates:

- Actual PipeGen GUI Pipeline IR and speed-report screenshots; app screenshots do not replace them.
- Venue/live hardware demonstration and its required execution evidence.
- Repository is now public. Verify current release-asset availability to judges and organizer acceptance of the linked export mechanism; historical private-access records remain preserved.
- Actual project-submission link and receipt. User reports the prerequisite feedback complete; the final project link is still awaited.

The application is verified as **recorded factory replay**. The hackathon submission is not marked complete.


## Current release/audit boundary

Public main includes the independent AI Camera Monitor; the existing dashboard has not undergone a visual redesign. The evaluation audit is isolated from the released baseline. Its 70 new passing fixture checks test metrics/alert/review-gate software, not model accuracy; the new 41-frame real evaluation still awaits host data and independent human annotation. No formal accuracy or new INT8/Jetson/closed-loop result is established. See `evaluation/int8-feasibility.md` and the forthcoming review-gated evaluation/reproducibility report. The user reports prerequisite feedback complete; final project receipt remains unconfirmed.
