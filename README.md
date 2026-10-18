# Hazard Zone Sentinel

**Turning ordinary cameras into real-time workplace safety intelligence.**

Source repository: [akilanpl/hazard-zone-sentinel](https://github.com/akilanpl/hazard-zone-sentinel) (private; authorized GitHub access required).

**Factory release:** `release/factory-safety` preserves the verified historical street baseline and adds an explicit isolated factory profile. Warehouse footage is downloaded and CPU-decode verified; matching factory metadata, a configured factory ROI and new PipeGen run remain pending; the existing street results below are historical evidence. See [factory status](docs/factory-release.md), [release artifact manifest](evidence/release-artifact-manifest.json) and [verified private draft export asset](docs/export-release-assets.md).

A local React + FastAPI safety operations application for CraftifAI PipeGen perception output. Tracked people entering normalized restricted polygons produce persistent incidents, live dashboard updates and optional JSONL output.

**Integration status:** genuine PipeGen metadata replay is integrated and verified: 1,029 frames, 7,688 person observations, 89 observed track IDs, and 33 computed polygon alerts in one replay session. These include 23 initial-inside observations and 10 observed outside-to-inside transitions. The original recorded video now plays in synchronization with those detections; this is recorded replay, not live camera inference. See [real replay](docs/real-pipegen-replay.md) for timestamp, tracking and benchmark limitations.

## Factory profile launch

Pending factory screen, with no historical fallback:

```bash
PORT=8002 ./scripts/start-factory-replay.sh
```

Second terminal:

```bash
SENTINEL_API_TARGET=http://127.0.0.1:8002 ./scripts/start-frontend.sh --port 5175 --strictPort
```

Open **http://127.0.0.1:5175**. After a genuine factory run, validate its paired manifest and set `SENTINEL_PROFILE_PATH` before starting. See [exact setup](docs/setup.md#factory-release-profiles). PENDING is intentional until verified matching assets arrive.

## Run genuine PipeGen replay

```bash
bash scripts/start-real-replay.sh /absolute/path/to/actual/metadata.json
```

Then run `bash scripts/start-frontend.sh`, open `http://127.0.0.1:5173`, and click **Start replay**. The full genuine metadata stays local; its fingerprint, a real frame excerpt, API/WebSocket/SQLite validation, and a real replay dashboard screenshot are included in `evidence/`. Replay uses its own database and explicit labels. [Instructions and verified semantics](docs/real-pipegen-replay.md).

## Run locally for synthetic QA

From this directory, install dependencies as described in [setup](docs/setup.md), then use two terminals:

```bash
SENTINEL_MODE=synthetic ./scripts/start-backend.sh
```

```bash
./scripts/start-frontend.sh
```

Open `http://127.0.0.1:5173`. Synthetic mode has distinct labels, explicit synthetic provenance and a separate SQLite database. Switch to `SENTINEL_MODE=live` for genuine data; it starts without demonstration incidents. Keep the default mode-specific database paths.

## Implemented application

- React/TypeScript industrial dashboard, detection metadata view and source/connection status.
- Polygon zone CRUD, normalized coordinates and validation.
- Bottom-center foot position, confidence thresholds, entry/exit/re-entry, per-track deduplication and stale-state expiry.
- SQLite incident history, acknowledgment, filters and analytics.
- FastAPI REST endpoints and WebSocket updates with frontend reconnect.
- Canonical detection/native analytics ingestion, optional JSONL export and a fail-closed PipeGen parser boundary.
- Explicit synthetic test controls and meaningful backend tests.

The backend remains usable while PipeGen is disconnected. Missing GPU/FPS/latency telemetry stays unavailable. This local prototype has no authentication and should bind localhost.

## Integration boundary

```text
Camera/video → CraftifAI PipeGen → ONNX/TensorRT → DeepStream tracked metadata
  → genuine metadata adapter → zone-entry engine → SQLite/JSONL → WebSocket/REST → dashboard
```

`POST /api/ingest/detections` consumes **our canonical schema**, shown in [the example](examples/canonical-detection.json), with normalized `[x1,y1,x2,y2]` bounding boxes. It is not a statement of PipeGen's native format. `POST /api/ingest/pipegen` intentionally returns 501 until `SENTINEL_PIPEGEN_PARSER=module:callable` is configured from genuine metadata. Read [integration instructions](docs/pipegen-integration.md).

## Verify

```bash
./scripts/check.sh
```

The frontend build includes TypeScript checking. Setup includes Codex bundled-runtime alternatives when npm or pip is absent on the host. See [verification results](docs/verification.md) for checks actually run; commands above are reproducible checks, not a claim they passed on every machine.

## Source guide

- `backend/`: API, data models, geometry, state engine, SQLite and adapter.
- `frontend/`: React application and Vite proxy.
- `tests/`: backend logic/API regression tests.
- `scripts/`: local launchers and explicit JSONL ingestion utility.
- `.env.example`, `examples/`: configuration and canonical data references.
- [Architecture](docs/architecture.md), [setup](docs/setup.md), [demo script](docs/demo-script.md).
- [GitHub/source handoff](docs/github-readiness.md), [seven-stage evidence ledger](evidence/checklist.json).
- [Submission checklist](docs/submission-checklist.md), [PipeGen export location](pipegen_export/README.md), [required real evidence](evidence/README.md).

Required genuine hackathon artifacts remain: real Pipeline IR screenshot, real TensorRT speed report, GPU DeepStream run, PipeGen export and actionable output connected to real source data. Synthetic application screenshots are not substitutes.

## Integration and recording handoff

- [Exact metadata contract](docs/canonical-schema.md) and [PipeGen operator handoff](docs/pipegen-handoff.md).
- [Footage recording guide](demo-video/README.md) and [90-second narration](docs/demo-script.md).
- [Expanded application QA](docs/application-qa.md) and [executed verification](docs/verification.md).

## Setup requirements and verified checks

Use **Python 3.12** for the tested locked environment and **Node 22.18+** for the complete checks (tested Node 24.19.0). Python source targets 3.10+, but execution on 3.10 has not been verified. The tested dependency versions are captured in `requirements-lock.txt` and `frontend/pnpm-lock.yaml`. No GPU, Docker, Redis or cloud database is needed for the application alone.

On a clean checkout with Python/pip and Node/npm available:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
cd frontend
npm install
cd ..
./scripts/check.sh
```

For a reproducible pnpm installation, use `pnpm install --frozen-lockfile --store-dir .pnpm-store` in `frontend/` instead of npm. [Setup](docs/setup.md) includes the already-installed Codex bundled runtime paths for this Linux host, where npm is absent.

Latest executed checks: **123 backend tests passed, 17 frontend tests passed, TypeScript passed, production build passed**. HTTP/WebSocket, browser interaction, persistent SQLite history, reconnect and synthetic/live isolation were also exercised. One upstream Starlette/AnyIO deprecation warning remains; genuine inference has not been tested by these checks. See [verification](docs/verification.md).

## API reference

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health`, `GET /api/status` | Application and source status; genuine telemetry when supplied |
| `GET /api/zones`, `POST /api/zones` | List/create normalized restricted polygons |
| `PUT /api/zones/{id}`, `DELETE /api/zones/{id}` | Edit/delete a zone; incident history is retained |
| `GET /api/incidents`, `GET /api/incidents/{id}` | Filtered history and incident details |
| `PATCH /api/incidents/{id}/acknowledge` | Acknowledge or unacknowledge |
| `GET /api/analytics/summary` | Counts and daily trends from SQLite |
| `POST /api/ingest/detections` | This application's canonical frame schema |
| `POST /api/ingest/pipegen` | Genuine metadata through an explicitly configured parser |
| `POST /api/synthetic/step` | Test generator; rejected in live mode |
| `WS /ws/live` | Frame, incident, status and zone updates |

Interactive OpenAPI documentation: `http://127.0.0.1:8000/docs` after starting the backend. Exact validation contracts are in `schemas/` and [canonical schema documentation](docs/canonical-schema.md).

## Real mode after genuine integration

Stop the synthetic backend. Configure the mapper only from actual PipeGen output, create matching camera zones in the separate live database, then run:

```bash
SENTINEL_MODE=live \
SENTINEL_PIPEGEN_PARSER=backend.adapters.field_mapping:parse \
SENTINEL_FIELD_MAPPING="$PWD/config/local-pipegen-mapping.json" \
./scripts/start-backend.sh
```

Keep the frontend running in the other terminal. Feed actual producer records through the configured adapter, using the [metadata handoff](docs/pipegen-handoff.md). Without a genuine mapping, start `SENTINEL_MODE=live ./scripts/start-backend.sh` to inspect an empty waiting-for-source dashboard; native ingestion deliberately remains unconfigured.

## Video credit and licensing

Prepared source footage: [Busy City Intersection with Pedestrians and Traffic](https://www.pexels.com/video/busy-city-intersection-with-pedestrians-and-traffic-36306747/) by **Nothing Ahead**, provided under the [Pexels License](https://www.pexels.com/license/). The original and losslessly remuxed test input remain on external storage and are excluded from Git. Respect the linked license and avoid implying endorsement. This credit does not relicense the footage as application source.

The selected input is `people-crossing.mp4`, H.264 MP4, 1920×1080, approximately 17.17 seconds. Its SHA-256 was checked against the PipeGen operator's provenance record. See [source provenance](demo-video/source-provenance.json) and [recording instructions](demo-video/README.md). This is source preparation only: the clip does not establish the same person's exit/re-entry, genuine detections, TensorRT performance or a real dashboard alert.

## Pending submission evidence

Genuine metadata and the explicitly labeled replay dashboard are now verified in [the ledger](evidence/checklist.json). Model/compiler summaries are partial evidence; the official Pipeline IR screenshot, full export and original run evidence still need packaging. Clearly named directories under `evidence/` cover Requirement/finalized flow, official Pipeline IR, actual model details, TensorRT FP16 report, DeepStream execution, real metadata and real-mode dashboard demonstration. Historical synthetic screenshots remain labeled; the new real replay screenshot is under `evidence/07-real-mode-dashboard/`.

## Synchronized real recorded video

Run `./scripts/start-synchronized-replay.sh` and `./scripts/start-synchronized-frontend.sh` in separate terminals, then open **http://127.0.0.1:5174**. These helpers verify the known original-video/metadata hashes before applying the inspected 33,366,700 ns timestamp offset. Video, raw metadata and databases remain outside Git.

The generic backend settings are `SENTINEL_REPLAY_VIDEO`, `SENTINEL_REPLAY_VIDEO_PTS_OFFSET_NS` and optional `SENTINEL_REPLAY_VIDEO_TOLERANCE_NS`; configure them only from verified media timing. See [synchronized replay setup and verification](docs/synchronized-video-replay.md) for exact paths, alternate ports, API Range support, metadata-only fallback and screenshots. Playback uses the presented video clock and never creates duplicate incident rows. The existing database retains 66 historical rows from two earlier 33-alert analysis sessions; the verified single-session analysis remains 33 alerts.
