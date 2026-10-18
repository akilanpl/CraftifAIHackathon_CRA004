# Executed verification — October 18, 2026

The application was implemented and verified locally. Real PipeGen integration and GPU inference were not exercised.

## Results

- `./scripts/check.sh`: **68 backend/adapter tests passed, 3 frontend regression tests passed**, TypeScript check passed, Vite production build passed.
- Backend coverage: polygon boundaries and invalid/overlapping polygons; entry/hold/exit/re-entry; multiple people and cameras; missing IDs, confidence and class filtering; malformed payloads; debounce, stale tracks and disconnection; persistence and acknowledgment; zone CRUD; native retries across restart; native/detection suppression; UTC timestamps; configured-parser provenance; live/synthetic isolation; WebSocket broadcasts.
- One upstream Starlette/AnyIO deprecation warning; no test failures.
- Production build: 1,582 modules; JavaScript 181.92 kB (56.93 kB gzip), CSS 18.77 kB (5.03 kB gzip). Output is `frontend/dist/`.
- Both exact launch scripts started successfully on localhost ports 8000 and 5173.
- `.venv/bin/python scripts/smoke_runtime.py`: **passed** against running servers through Vite's HTTP and WebSocket proxies. Verified actual transport, stored synthetic entries, repeated-frame suppression, exit/re-entry, acknowledgment and provenance. The script refuses mutation in live mode.
- Browser QA: synthetic button produced boxes and incidents; zone name edit saved; incident detail and acknowledgment updated; critical-severity filtering yielded the correct empty state; narrow-screen navigation reached analytics. Desktop and narrow layouts were inspected.
- Python sources parse using Python 3.10 grammar. Execution used Python 3.12; a Python 3.10 runtime test was not performed.
- Shell launcher syntax and example JSON checked. Temporary QA servers were stopped after verification.

## Environment and dependencies

Already present: system Python 3.10.12 and Git 2.34.1; bundled Node 24.19.0, Python 3.12.14, pip, pnpm 11.25.0. Host PATH had no Node/npm and system Python lacked pip. No runtime was downloaded.

New project dependencies: FastAPI 0.115.14, Uvicorn 0.34.3 plus standard WebSocket/runtime extras, Pydantic 2.14.1, pytest 8.4.2, httpx 0.28.1; React/ReactDOM 18.3.1, Lucide React 0.468.0, Vite 5.4.21, TypeScript 5.9.3, React plugin 4.7.0 and types. Exact transitive versions are in `requirements-lock.txt` and `frontend/pnpm-lock.yaml`. Dependencies came from PyPI/npm; pnpm retains integrity hashes. Only esbuild's required installation hook was enabled.

Python packages use `.venv`; frontend packages use `frontend/node_modules`; development pnpm store is outside the deliverable under the chat's `work/` directory. Approximately 1.4 GB root space remained. No models, video, Docker, CUDA, drivers or system packages were installed or changed.

## Evidence boundary and remaining work

`evidence/synthetic-dashboard.jpg` and `synthetic-analytics-mobile.jpg` are **synthetic application QA only**, not proof of PipeGen or real workplace activity. QA records were written to a separate temporary synthetic database outside the source deliverable. Production data was not seeded.

Needed from the PipeGen operator: genuine tracked metadata samples (outside, inside, exit), actual export, delivery transport, timestamp/frame/bbox/track semantics, optional native event IDs, real telemetry and optional annotated video URL. Configure `SENTINEL_PIPEGEN_PARSER=module:callable` from those samples and validate real input. Native ingestion deliberately returns 501 while unconfigured in live mode.

Submission remains pending real Pipeline IR screenshot, actual TensorRT compilation speed report, GPU DeepStream run and end-to-end real incident evidence. Track occupancy is held in memory; restarting the backend loses detection occupancy and the next inside observation can generate a new entry. Native event IDs and incident history persist in SQLite. Use one authoritative metadata mode per camera/zone.

## Expanded submission-readiness verification

Final `./scripts/check.sh` completed successfully after all fixes: 68 pytest cases, 3 native Node regression cases, TypeScript and production Vite build. No new dependencies were installed during this follow-up.

An actual browser-created four-point zone was dragged, saved and reloaded. `scripts/qa_runtime.py` verified two simultaneous people, outside/entry/hold/exit/re-entry, live WebSocket incident delivery, API filtering/detail/acknowledgment toggles, analytics and a separate SQLite connection. Its SQLite path can be selected with `--db`; it requires the described Browser QA Zone in synthetic mode. Browser JSON export was downloaded and parsed: exactly three filtered synthetic incidents.

Backend restart retained all three multi-person records and two acknowledgment states. Automatic WebSocket reconnect and cleared offline errors were visible without reloading. A separate live-mode database had zero zones/incidents, rejected synthetic generation with 409 and rejected unconfigured native PipeGen ingestion with 501. No test fixture was sent as real PipeGen input.

`schemas/` was generated from actual validation models. Both canonical and artificial mapping examples passed the local-only metadata validator, which makes no network calls or database writes. Python source and JSON templates were checked. The evidence ledger has exactly seven genuine stages, all PENDING. New screenshot `evidence/synthetic-submission-qa.jpg` is synthetic QA only.

Read-only installed-resource inspection found `/opt/PipeGen/PipeGenApp`; external workspace exists at `/mnt/seagate4/PipeGenHackathon`. Format preparation uses official CraftifAI/NVIDIA sources in `demo-video/README.md`; actual PipeGen version-specific format acceptance remains pending. No PipeGen download, Docker/containerd operation, mount change or GPU workload was performed.
