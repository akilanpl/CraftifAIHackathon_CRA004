# Local setup

Run from the repository root (`outputs/hazard-zone-sentinel` in this delivery). Keep files here or copy the complete repository to a suitable local workspace. No Docker, GPU runtime or system changes are needed to run the application. Python source targets 3.10+; verification in this Codex session uses bundled Python 3.12 and Node 24. The application can build with Node 18+, while the complete check script uses Node 22.18+ (or the already available bundled Node 24) for native TypeScript regression tests.

## Existing environment

The primary development agent inspected tools and storage before installation. Host Python 3.10 lacks pip. Codex includes Python 3.12, Node 24 and pnpm; use those rather than downloading runtimes. The root partition had approximately 1.6 GB free during implementation, so do not place models, footage or engines there. See the final QA record for installed dependency and test results.

For this machine only, make the bundled runtimes available if standard tools are missing:

```bash
export PATH="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin:$PATH"
PNPM="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/fallback/pnpm"
```

## Dependencies

Reuse the delivered `.venv` and `frontend/node_modules` if present and compatible. On a clean clone:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
cd frontend
npm install
cd ..
```

`requirements-lock.txt` captures the tested Python 3.12 environment. For another supported Python version, use `requirements.txt` if a locked platform-specific dependency is incompatible.

On this Codex machine, substitute `"$PNPM" install --store-dir .pnpm-store` for `npm install`. Prefer the delivered pnpm lockfile with `"$PNPM" install --frozen-lockfile --store-dir .pnpm-store` for reproducible installs. Do not install both package-manager trees. The delivered pnpm workspace configuration allows the required esbuild install hook. The launcher executes the installed Vite binary directly, so starting the app does not invoke an implicit package-manager install. Configuration uses shell environment variables; `.env.example` is a reference, not auto-loaded.

## Start live mode

In terminal 1:

```bash
SENTINEL_MODE=live ./scripts/start-backend.sh
```

In terminal 2:

```bash
./scripts/start-frontend.sh
```

Open `http://127.0.0.1:5173` and API docs at `http://127.0.0.1:8000/docs`. Vite proxies `/api` and `/ws` to port 8000. `PORT` may change the backend listener, but the Vite proxy must then be updated to match. Launch one backend worker. Production build output is not an independent backend host; deploy with an API/WebSocket reverse proxy when needed.

Live mode defaults to `data/sentinel.sqlite3`. It starts without incident examples, synthetic metadata or invented telemetry. Configure zones and connect a genuine source. `/api/ingest/pipegen` returns 501 until the native parser is configured.

## Start synthetic test mode

Stop the live backend first and run:

```bash
SENTINEL_MODE=synthetic ./scripts/start-backend.sh
```

This uses `data/synthetic.sqlite3` by default. Keep `SENTINEL_DB_PATH` unset to preserve database separation. Use the dashboard synthetic step control to exercise outside → entry → hold → exit → re-entry. Records carry synthetic provenance. See `demo-script.md`.

## Configuration

| Variable | Default / meaning |
| --- | --- |
| `SENTINEL_MODE` | `live` or explicit `synthetic` |
| `SENTINEL_DB_PATH` | Mode-specific SQLite file; parent directory created |
| `SENTINEL_JSONL_PATH` | Unset; optional append-only incident export |
| `SENTINEL_TRACK_TIMEOUT` | 5 seconds of missing observation before track state expires |
| `SENTINEL_SOURCE_TIMEOUT` | 10 seconds before metadata source becomes stale |
| `SENTINEL_PIPEGEN_PARSER` | Unset; actual `module:callable` native metadata parser |
| `PORT` | 8000; start script listener only |

## Checks

```bash
./scripts/check.sh
```

The build runs TypeScript checking before Vite. The check script uses installed Node binaries directly and supports the bundled runtime. `npm run build` also works when npm is available. Troubleshooting: confirm backend `/api/health`; check the browser errors; confirm correct port and synthetic/live mode. A connected API with no metadata is an expected state, not successful PipeGen integration.
