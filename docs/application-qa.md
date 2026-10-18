# Application QA

All test detections and incidents used during application validation are synthetic. These checks do not establish a real camera run, PipeGen execution, TensorRT inference, or GPU performance.

## Frontend verification

Executed against the completed application source:

- TypeScript project check: passed.
- Vite production build: passed; 1,582 transformed modules, 181.92 kB JavaScript (56.93 kB gzip).
- Three frontend domain regression checks: passed. They cover retained incident filtering after zone deletion, deduplication and renamed-zone labels, pointer-coordinate normalization including SVG borders, clamping a vertex dragged beyond the frame, and consistent coordinates after a canvas resize.

Commands (from `frontend/`, using Node 24 in the build environment):

```sh
node tests/domain.test.ts
node node_modules/typescript/bin/tsc -b
node node_modules/vite/bin/vite.js build
```

The domain test file uses Node's built-in test runner with native TypeScript stripping (Node 22.18+ or Node 24). It requires no added testing dependency. This helper-level test does not replace browser interaction testing.

## Frontend defects corrected during QA

- Zone update bodies omit the backend-generated ID, so strict backend validation accepts edits.
- Deleted zones remain available in incident-history filters because incidents persist independently of current zone configuration.
- Pointer coordinates account for SVG borders and remain in the normalized 0–1 range when dragged off the canvas.
- WebSocket reconnect triggers a complete data refresh, and callbacks from disposed sockets do not change current application state.
- Disconnect clears detection overlays rather than leaving a previous frame presented as current.
- Backend connection errors clear on successful recovery; mutation validation errors remain separately dismissible.
- Incident details synchronize with refreshed persisted records, including acknowledgment changes from another client.
- Synthetic controls are disabled while the backend is offline.
- A healthy backend without active source metadata displays `WAITING FOR SOURCE`; synthetic mode retains its prominent test label.
- Source freshness and the backend connection are displayed separately. Idle metadata is labeled as the last received frame.
- FPS, latency, and GPU are shown only when supplied by backend telemetry.
- Zone edit controls retain and expose the entry debounce setting. Saved zone names and camera IDs are trimmed.
- Metadata overlays share the actual incoming frame aspect ratio with a configured video element.
- Incident rows expose a short ID, while incident details and exported JSON retain full IDs and provenance.

## Scope of verification

The helper checks and production compilation above were executed directly by the frontend QA worker. Synthetic end-to-end engine/API checks and actual browser interaction results are recorded separately by the coordinating worker; they must not be inferred from the helper tests. The remaining real-world integration evidence still requires genuine PipeGen output and the hardware pipeline.

## Coordinated browser and runtime checks

The primary agent verified all six sections, polygon creation/drag/save/reload, invalid drafts, zone deletion cancellation/confirmation, retained historical filters, severity/event/zone filtering, incident details/acknowledgment, JSON download content, metadata display and analytics. The UI-created polygon drove a multi-person HTTP/WebSocket test verified against SQLite. Restarting the backend retained incidents and acknowledgment; the browser showed offline status, disabled synthetic controls, then reconnected automatically without reload. Switching to a separate empty live database cleared synthetic rows and frames and showed WAITING FOR SOURCE. Synthetic controls were absent and the synthetic endpoint rejected requests in live mode.

A native window.confirm dialog stalled browser automation during deletion QA. It was replaced with an accessible application confirmation dialog; both cancellation and deletion were verified afterward. Final TypeScript/build passed after that change. No real video stream was available to validate playback; it remains part of genuine integration.
