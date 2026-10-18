# Source handoff and GitHub readiness

## Physical source location

The repository is an ordinary local directory, verified with `realpath` and `stat`:

```text
/home/vijayababu/Documents/Codex/2026-10-18/files-pasted-by-the-user-mission/outputs/hazard-zone-sentinel
```

`stat` reported a directory owned by `vijayababu`, mode `775`; its README is a regular file owned by `vijayababu`, mode `664`. `git rev-parse --show-toplevel` resolved to that same directory. These checks establish a physical filesystem source directory rather than a hosted-only artifact. They do not imply that a remote GitHub repository exists.

The authenticated GitHub account is `akilanpl`. The private repository is https://github.com/akilanpl/hazard-zone-sentinel and `origin` is `https://github.com/akilanpl/hazard-zone-sentinel.git`. The known-good baseline is preserved on `main`; factory release work uses the separate `release/factory-safety` branch. Final branch push/commit status is reported by the primary agent. Repository visibility remains private; public publication has not been authorized. Credentials are kept outside this source repository.

## Exact launch commands on this host

Terminal 1, synthetic application rehearsal:

```bash
cd /home/vijayababu/Documents/Codex/2026-10-18/files-pasted-by-the-user-mission/outputs/hazard-zone-sentinel
SENTINEL_MODE=synthetic ./scripts/start-backend.sh
```

Terminal 2:

```bash
cd /home/vijayababu/Documents/Codex/2026-10-18/files-pasted-by-the-user-mission/outputs/hazard-zone-sentinel
./scripts/start-frontend.sh
```

Open `http://127.0.0.1:5173`; backend API docs use `http://127.0.0.1:8000/docs`.

For genuine metadata, stop the synthetic backend and launch `SENTINEL_MODE=live ./scripts/start-backend.sh` from the same directory. Native PipeGen input deliberately returns 501 until its real-schema parser is configured. Dependency setup and parser configuration are documented in `setup.md` and `pipegen-integration.md`.

Run the verification entry point from that directory:

```bash
./scripts/check.sh
```

## Source boundaries

Include application source, tests, scripts, lockfiles, configuration examples, docs and clearly labeled small QA screenshots. `.gitignore` excludes virtual environments, Node dependencies, databases, runtime JSONL/logs, build output, local secret files, models, TensorRT engines, large videos and archives. Gitignore is a convenience, not a secret scanner: review staged paths and content before any future publication. Keep necessary large artifacts externally and reference their manifests or locations in the export/evidence documentation.

Use the existing `frontend/pnpm-lock.yaml` and `requirements-lock.txt` for reproducibility. Do not commit `.env` or camera credentials. Use `.env.example` to communicate variable names.

## Submission state

The application implementation and synthetic verification are ready for review. Genuine metadata and the real recorded replay dashboard are verified in `../evidence/checklist.json`; model/compiler/execution summaries are partial, and remaining official screenshots/exports still need packaging. A working synthetic application is not completion of the perception track. Capture genuine evidence, configure the actual metadata parser, verify real-mode behavior, and review the submission checklist before making the private repository public or submitting it for judging.


## Factory release assets

The historical export is preserved as a verified asset in a private draft release; see `export-release-assets.md`. The draft is not final hackathon submission and requires authenticated repository access. Factory assets remain pending. Use the profile launch commands in `setup.md#factory-release-profiles` to show an honest pending factory state, without relabeling the historical street source.
