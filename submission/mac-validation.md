# Mac software validation

Baseline: `ca5d3668a06a2acf2f08883b4dfafb51f80bd4e5`. Executed October 18, 2026 on Darwin arm64, Python 3.12.14, Node 24.19.0 and pnpm 11.25.0. No application runtime code or package versions changed. The existing alert-audit fixture now writes its fresh timing report into pytest temporary storage, preserving committed historical evidence.

| Check | Actual result |
|---|---|
| Unchanged baseline: `bash scripts/check.sh` | 234 backend passed, 5 skipped; 89 frontend passed; TypeScript and production build passed. |
| Final: `bash scripts/check.sh` | 236 backend passed, 5 skipped; 89 frontend passed; TypeScript and production build passed. Two new tests account for the increase. |
| `bash scripts/mac/final-e2e.sh` | PASS: real HTTP/WebSocket integration against the existing FastAPI application. |
| Factory and new integration tests | Full 254-frame genuine export processed; hash-tampered copy rejected before service launch. |
| Browser smoke | BLOCKED: installed Chromium aborted with SIGABRT during launch in this environment; no browser assertions completed. |
| Original MP4/video overlay synchronization | NOT RETESTED: matching video unavailable in inspected local project/attachment assets. |
| Independent CPU model execution | NOT RUN: local YOLOv8m model unavailable in inspected assets. |

Five optional tests skipped: three real-worker HTTP/WebSocket source tests need the external model/service and genuine JPEG fixtures; one decoder test needs NumPy; one real-model validation needs the external ONNX model. The same five skips occurred on unchanged baseline. The two pre-existing warnings are the Starlette/AnyIO deprecation and replay-video GET/HEAD duplicate OpenAPI operation ID. Neither was suppressed.

Logs: [baseline regression](baseline-check.txt), [final regression](final-check.txt), [focused factory/E2E/optional checks](focused-check.txt). [Machine-readable E2E result](mac-e2e-result.json) and [preserved baseline hashes](preservation.json).

## Reproduce from a clean Mac clone

Use Python 3.12, Node 24 (22.18+ for native TypeScript tests) and pnpm. Install the existing pinned dependencies:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
pnpm -C frontend install --frozen-lockfile
bash scripts/check.sh
bash scripts/mac/final-e2e.sh
# Optional: save a fresh run report at a chosen writable location.
bash scripts/mac/final-e2e.sh --output /absolute/path/to/mac-e2e.json
```

No video, model, GPU, new service framework or additional Python package is required for metadata integration. Network is needed only to obtain dependencies, not to run the check. The unchanged baseline suite regenerated a handler-timing report under committed evidence; that file was restored byte for byte. The fixture now writes fresh reports to the pytest temporary directory instead, retaining every existing assertion and leaving the historical record unchanged.

## What the network check executes

The harness validates the original metadata SHA-256 before launching anything. It starts the existing `backend.main:app` with its production ReplayController on a pre-bound ephemeral localhost port and temporary SQLite database. It configures the exact warehouse camera/ROI from the unchanged profile through the zone API. It uses the existing metadata-only replay path, without pretending that its legacy profile is a READY video/metadata pair. No asset guard is bypassed or profile forged.

It delivers all 254 frames through `/api/replay/start`, verifies 522 observations, all six original IDs, frame/source IDs and PTS, and checks the explicitly labeled replay-session clock. All 254 frames arrive over `/ws/live`. The existing engine persists exactly two entry incidents at frames 38 and 66. Inspection of delivered tracked positions observes two exits, one re-entry and 43 continued-inside holds. Exits are observed transitions, not newly invented persisted incident types.

Pause/resume, read-only timeline queries in seek order, stop, WebSocket disconnect/reconnect, incident detail/acknowledgment and analytics are checked. Restarting the backend with the same temporary QA database preserves both incidents and acknowledgment. **Explicit “Analyze new session” intentionally starts another analysis and may persist another pair of incidents; it is not a video restart.** The harness does not change that established behavior.

Separate synthetic and independent-AI services exercise source isolation. The AI service runs its labeled nine-step simulation with inference explicitly unavailable; stopping it leaves warehouse health/history intact. No real CPU prediction is claimed. All child services and temporary databases/logs are cleaned on normal completion or assertion failure.

The React application passed its existing 89 tests, type-check and production build. All eight navigation views remain in the unchanged frontend source. Fresh browser-level rendering and video synchronization are not established by a build.

## Preservation

The [preservation record](preservation.json) matches current metadata, engine report, warehouse ROI/profile, release audit and production backend source hashes. All previously tracked files in `evidence/` remain unchanged. No pre-existing production database was present in this isolated clone; E2E services use only their temporary directory. No existing host services are restarted. This Mac result verifies application behavior against recorded output, not a new PipeGen, TensorRT or NVIDIA run.
