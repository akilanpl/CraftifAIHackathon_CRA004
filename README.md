# Hazard Zone Sentinel

**Turning ordinary cameras into real-time workplace safety intelligence.**

Source repository: [akilanpl/hazard-zone-sentinel](https://github.com/akilanpl/hazard-zone-sentinel) (private; authorized GitHub access required).

A local React + FastAPI safety operations application for CraftifAI PipeGen perception output. Tracked people entering normalized restricted polygons produce persistent incidents, live dashboard updates and optional JSONL output.

**Integration status:** the application and synthetic test workflow are implemented. The real PipeGen installation, native metadata mapping, TensorRT compilation/speed report and live DeepStream run are pending external integration. No model, live camera inference or benchmark result is fabricated. PipeGen is the required actual vision pipeline.

## Run locally

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

Latest executed checks: **68 backend/adapter tests passed, 3 frontend tests passed, TypeScript passed, production build passed**. HTTP/WebSocket, browser interaction, persistent SQLite history, reconnect and synthetic/live isolation were also exercised. One upstream Starlette/AnyIO deprecation warning remains; genuine inference has not been tested by these checks. See [verification](docs/verification.md).

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

All seven genuine evidence stages remain **PENDING** in [the ledger](evidence/checklist.json). Clearly named directories under `evidence/` cover Requirement/finalized flow, official Pipeline IR, actual model details, TensorRT FP16 report, DeepStream execution, real metadata and real-mode dashboard demonstration. Existing screenshots are explicitly synthetic application QA.
