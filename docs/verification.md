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

`schemas/` was generated from actual validation models. Both canonical and artificial mapping examples passed the local-only metadata validator, which makes no network calls or database writes. Python source and JSON templates were checked. At that earlier synthetic-only verification, the ledger had seven genuine stages pending. The real replay milestone below supersedes that status. New screenshot `evidence/synthetic-submission-qa.jpg` is synthetic QA only.

Read-only installed-resource inspection found `/opt/PipeGen/PipeGenApp`; external workspace exists at `/mnt/seagate4/PipeGenHackathon`. Format preparation uses official CraftifAI/NVIDIA sources in `demo-video/README.md`; actual PipeGen version-specific format acceptance remains pending. No PipeGen download, Docker/containerd operation, mount change or GPU workload was performed.


## Genuine PipeGen replay verification — October 18, 2026

- Final full backend suite: **82 passed** (one existing Starlette/AnyIO deprecation warning).
- Frontend domain tests: **7 passed**; TypeScript and Vite production build passed.
- Full actual source replay through HTTP/WebSockets: 1,029 frames and 7,688 person detections received; every normalized bbox checked against its original pixel values.
- 89 observed person tracker IDs, not verified physical people. Original raw file SHA-256 unchanged.
- 33 computed alerts for the original restricted polygon: 23 initial-inside observations, 10 observed outside-to-inside entries. 11 observed exits, no observed reentry; 2,458 repeated inside observations did not create alerts.
- 33 incidents independently read from SQLite; acknowledgment persisted. Latest-frame visible occupancy is three, separate from retained deduplication state.
- The actual React dashboard was opened and replayed at 1x; completion, boxes, IDs, 33 alerts and replay labels were visually checked and captured.
- Native occupancy tags/counts agree; bottom-center geometry differs on 52 frames. See `real-pipegen-replay.md`.
- These checks replay recorded metadata. They do not rerun inference, verify power draw, establish ground-truth people identities, or prove a synchronized video feed.

Reproduce actual-source validation against a **new** verification database:

```bash
.venv/bin/python scripts/verify_real_replay.py /absolute/path/to/actual/metadata.json --db data/new-verification.sqlite3 --report data/replay-verification.json
```

## Synchronized recorded-video feature verification

Latest suite: **103 backend tests + 15 frontend tests passed**, TypeScript and Vite production build passed. Read-only video/timeline transport, strict timestamp matching and shared normalized foot-point membership were added. The isolated unchanged-source regression still yields 33 computed alerts (23 initial-inside + 10 entries), and verifies all 1,029 frames / 7,688 person observations over HTTP/WebSocket, SQLite and acknowledgment persistence. Existing 66 historical rows and all acknowledgment states remained unchanged during actual video controls.

The original video was fully CPU-decoded using installed GStreamer; all 1,029 raw buffer PTS matched metadata, with verified browser offset 33,366,700 ns. Actual browser playback, visual alignment at early/middle/late frames, pause/resume, seeks, 2× rate, ended state and narrow/desktop viewport geometry were observed. No new GPU inference was run. Detailed evidence, configuration and limitations: `synchronized-video-replay.md`.


## Factory release branch checks

The current release preparation passes **123 backend tests**, **17 frontend tests**, TypeScript, and the production frontend build. Profile tests cover file pairing, timestamps, dimensions, source, explicit polygons, missing/invalid profiles, asset mutation, database restart and cross-profile rejection. Browser checks verified the PENDING factory view has zero history and no substituted video; the historical engine evidence page renders; historical playback still aligns with its SVG. The full original source regression independently reproduced 33 alerts, persisted acknowledgment and history through restart, and reconnected WebSockets twice. See `evidence/07-real-mode-dashboard/release-baseline-regression.json`.

The reusable CPU-only verifier decoded all 1,029 original frames and reproduced its +33,366,700 ns mapping. New factory timing/visual correctness, new incident counts, official PDF compliance and new export remain PENDING. These checks do not rerun GPU inference.


## Follow-up hardening and official PDF review

**133 backend tests and 22 frontend tests passed**, plus TypeScript and the production build. The standard check script now includes deferred-request race tests. Profile validation rejects malformed MP4 containers, disallows mismatched pending-zone cameras and binds model/camera identity to history. Container validation does not claim codec decodability. The actual warehouse input passes the structural check.

Browser regression verified paused seek to original frame102 with -299 ns difference, 2× playback through ENDED at frame1028, replay after ending, repeated reload to paused frame0, and recovery after the Vite development process was restarted. Historical incident history remained66rows. The factory view remains PENDING without substituted detections. Official seven-page PDF reviewed; page-mapped checklist and entry-form handoff added. User selected **4 PM IST on October18** as cutoff.


## Final warehouse recorded integration

Final suite: **136 backend tests,25frontend tests**, TypeScript and production build passed. Actual new metadata is254frames/522person observations/6trackIDs. Exact generated polygon produces2observed entries including1reentry,2exits,0initial-inside events,43hold observations. NativeROIgeometry differs on9frames and is not forced to agree. Original pixel box values and equal SVG/video rectangles were checked at decoded frames25/50/75/100; sampled PTS deltas zero. Actual warehouse service restart retained both incident IDs and acknowledgment states; browser playback/seeks retained2rows. RequestedURL `http://127.0.0.1:5173/` now targets the isolated warehouse backend8003. No street incidents were moved or deleted.
