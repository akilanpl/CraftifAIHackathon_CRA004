# Hazard Zone Sentinel

**Turning ordinary cameras into real-time workplace safety intelligence.**

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
