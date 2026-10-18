# Synchronized original video + genuine PipeGen detections

The dashboard now plays the original recorded MP4 behind actual PipeGen person detections, original candidate tracker IDs/confidence, and the configured normalized restricted polygon. **REAL PIPEGEN REPLAY is recorded playback, not a live camera or a new inference run.** Metadata-only and synthetic modes remain available.

## Launch the verified existing clip

From the repository root, in two terminals:

```bash
./scripts/start-synchronized-replay.sh
```

```bash
./scripts/start-synchronized-frontend.sh
```

Open **http://127.0.0.1:5174**. Backend API: http://127.0.0.1:8001. These ports preserve the pre-existing application on 8000/5173. The frontend uses the same `/api` and `/ws` proxy pattern; `SENTINEL_API_TARGET` overrides its backend target. Use the video controls, not the separate optional incident-analysis controls, for pause/play/seek/repeat.

The launcher selects `/home/vijayababu/Videos/people-crossing.mp4` or the readable external copy `/mnt/seagate4/PipeGenHackathon/demo/people-crossing.mp4`, with the actual metadata export at `/home/vijayababu/.pipegen/varunvbabu/c74acf17-f432-4f7a-ac13-c48b447ccf1a/output/metadata.json`. Optional positional arguments are metadata path then video path. Both inputs are read-only. The launcher verifies both SHA-256 hashes before applying this recording's verified timing configuration. It refuses mismatching files rather than guessing their alignment.

For a different reviewed pair, explicitly configure the backend:

```bash
PORT=8001 \
SENTINEL_REPLAY_VIDEO=/absolute/path/to/recorded.mp4 \
SENTINEL_REPLAY_VIDEO_PTS_OFFSET_NS=VERIFIED_INTEGER_OFFSET \
SENTINEL_REPLAY_VIDEO_TOLERANCE_NS=8350000 \
bash scripts/start-real-replay.sh /absolute/path/to/genuine/metadata.json
```

`VERIFIED_INTEGER_OFFSET` is a placeholder, not a usable value. An absent offset withholds detection boxes. The API does not accept filesystem paths from URL/query parameters. Only the explicitly configured, readable MP4 is served. `/api/replay/video` supports GET, HEAD, full/open/suffix byte ranges and 416 responses. `/api/replay/timeline` exposes validated normalized detections and raw PTS, without arbitrary raw metadata fields or secret filesystem paths.

## Verified timing and coordinate system

The paired video SHA-256 is `cfb10db5adb8869240e78ef68185f429a52efac1054b26aca4ccc3534c6094b5`. It is H.264 High Profile MP4, 1920×1080, 60000/1001 FPS, seekable, duration 17.167167167 seconds. Both existing copies have the same hash and are readable.

The unchanged metadata SHA-256 is `ae10cfba371d2d553f4804058240e56ade5653c83c86916f354892c55df6d941`. All **1,029** frames were CPU-decoded with existing GStreamer tools and each original video buffer PTS was compared to the metadata frame at the same index: **zero mismatches**. The video segment starts at 33,366,700 ns and maps that point to stream time zero. Chromium's first `requestVideoFrameCallback` reports media time zero, confirming:

```text
metadata PTS ns = presented video mediaTime seconds × 1,000,000,000 + 33,366,700
```

The default tolerance is **8,350,000 ns**, approximately half one source-frame interval. Matching is an immutable binary search of actual timestamps. Missing/unverified/out-of-tolerance frames produce no boxes; detections are never interpolated. The first two source frames genuinely have no person observations and therefore show no boxes. Browser callback precision produces sub-microsecond rounding deltas in the inspected samples.

`requestVideoFrameCallback.mediaTime` drives overlay selection. The fallback samples `video.currentTime` using animation/timeupdate events, with the same strict matcher; this fallback was logically tested but the observed browser uses rVFC. Paused frames remain selected. Seeking withholds boxes while decoding, then matches the presented target frame. Playback speed changes require no metadata timer adjustment. Ended playback retains the final actual presented frame.

The video and SVG share an exact 1920:1080 viewport, including the same contain/letterboxing geometry. Their measured rectangles were identical at desktop and 585px document width. Source-dimension mismatch withholds person and polygon overlays rather than claiming alignment.

## Incident history is separate from playback

Video playback, pause, seek, speed changes and reaching/restarting the clip call no incident-ingestion endpoint. The timeline and video endpoints are read-only. Red person highlighting is transient bottom-center polygon membership with the zone confidence threshold; it does not invent an event. Zone edits change application highlighting/analysis, never the original detections.

A clean event-engine regression against the unchanged export still produces **33 computed alerts: 23 first-observed-inside + 10 observed entries**, 11 previously audited exits and zero observed re-entries. The helper regression again verified 1,029 HTTP/WebSocket frames, all 7,688 person observations, 89 observed candidate IDs, SQLite persistence and acknowledgment.

Before this feature's browser QA the existing database already contained **66 rows from two prior 33-alert analysis sessions**. Those complete records and acknowledgment states remained unchanged after repeated video playback, seeking, resizing, speed changes and reconnect. History is retained rather than deleting a prior session to force a particular total. The collapsed optional metadata-analysis action intentionally creates a distinct analysis session and can append another set; it is not the video play button.

## Verification and screenshots

Final feature checks: **103 backend tests, 15 frontend tests, TypeScript and production build passed**. Backend video transport tests include ranges, HEAD, invalid/missing files, mode isolation and read-only timeline behavior. Original replay/synthetic/API tests also pass.

Actual browser playback and visual box alignment were observed near **1.70, 4.50, 6.86 and 15.45 seconds**. Pause/resume, forward/backward seeks, 2× playback, clean completion and responsive resizing were exercised. Real Range responses through Vite matched exact bytes from the original MP4. WebSocket updates, independent SQLite reads, immutable incident records and original metadata hash were checked.

Evidence in `evidence/07-real-mode-dashboard/`:

- `synchronized-real-video.jpg`: actual desktop browser video with original boxes/red zone.
- `synchronized-overview.jpg`: recorded video, actual overlays and persisted alert history together.
- `synchronized-real-video-mobile.jpg`: narrow-layout browser capture.
- `video-pts-verification.json`: full decoded-frame PTS comparison.
- `browser-video-sync-observations.json`: observed presented-frame timing and viewport geometry.
- `synchronized-video-verification.json`: transport/persistence/no-duplication summary.
- `synchronized-source-replay-regression.json`: isolated event-engine regression; its metadata-only scope describes that test helper, not the video viewer.

The clip is credited to Nothing Ahead under the linked Pexels License in the README. No video, raw full metadata, engine, model or database is committed. No TensorRT compilation, model training, Docker/driver/mount change or new inference was performed. Original capture UTC and ground-truthed physical identities/re-entry remain unavailable; synchronized playback does not establish them.
