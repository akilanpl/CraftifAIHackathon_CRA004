# Replay synchronization helper checks

The pure matching helper in `frontend/src/replaySync.ts` selects an actual metadata record by binary search. Inputs must have a validated, strictly increasing immutable `pts_ns` timeline. Run `validMetadataTimeline` once when loading metadata. Matching uses `video media time × 1e9 + verified PTS offset`, with a caller-supplied strict tolerance. An unverified/null offset, invalid time or absent nearby observation returns no match. No boxes are interpolated and no incidents are persisted by this helper.

Executed with the existing bundled Node 24 runtime:

```bash
node --experimental-strip-types --test --test-isolation=none frontend/tests/replaySync.test.ts
```

Result: **7 tests passed**. Coverage: exact/original-frame selection; missing metadata and clip boundaries; tolerance boundaries and deterministic midpoint ties; paused repeated samples; backward/forward seek without stale state; rate-dependent media-time advancement; explicit offsets without guessing from the first metadata PTS; invalid input/timeline validation.

These are logical timestamp tests. They do not establish that a specific video's people visually align with its boxes, that its PTS offset is correct, or that browser rendering works. Actual media/container timing inspection and browser observation must establish those separately. A 59.94 FPS timeline has approximately 16.683 ms between frames; a roughly half-frame tolerance is appropriate only after inspecting the actual timeline and source timing.

Actual whole-file PTS and browser rendering verification is now complete for the documented video pair. All 1,029 raw video PTS match the metadata, the stream origin is independently inspected, and visual alignment was observed at four points. See `synchronized-video-replay.md` and the structured evidence under `evidence/07-real-mode-dashboard/`. The fallback without rVFC remains logical-test coverage rather than a separately observed browser path.
