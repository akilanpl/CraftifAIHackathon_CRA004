# Real PipeGen replay dashboard

`real-pipegen-replay-dashboard.jpg` is a genuine browser capture after replaying the actual 1,029-frame export. It shows 33 computed alerts, 3 people inside the polygon in the latest frame, original candidate tracker IDs, and explicit REAL PIPEGEN REPLAY / metadata-only labels. This is neither synthetic QA nor a synchronized live camera view.

A fresh replay session persists a separate set of computed alerts; history across sessions includes repetitions. Original capture UTC remains unavailable; synchronized recorded video is now verified as described below.

## Synchronized recorded-video improvement

The earlier screenshot above describes the previous metadata-only implementation. `synchronized-real-video.jpg`, `synchronized-overview.jpg` and `synchronized-real-video-mobile.jpg` now document actual original-video playback with genuine detections and the red polygon. The PTS and browser-verification JSON reports establish the matching source pair and observed alignment. This remains recorded replay, not live camera inference. The original metadata hash and the per-analysis 33-alert result are unchanged. Existing 66 rows are two retained earlier sessions; video QA added none.
