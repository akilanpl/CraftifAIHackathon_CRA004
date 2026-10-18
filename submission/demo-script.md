# Demo script

1. Open the [project README](../README.md) and show the four Track A requirements, genuine artifacts and exported pipeline link. Explain that PipeGen generated the perception workflow.
2. On Mac, run `bash scripts/mac/final-e2e.sh`. Narrate: “This is RECORDED METADATA REPLAY. The test simulates delivery of genuine prior PipeGen output through the existing application. It does not execute NVIDIA inference.”
3. Show the resulting 254 WebSocket frames, 522 observations, six original tracking IDs, two entry incidents, two observed exits, one re-entry and 43 suppressed holds. Explain the replay-session clock and original PTS fields.
4. Show acknowledgment recovery after backend restart and matching incident/analytics totals. Synthetic and independent-AI sessions use separate temporary storage. All QA services stop automatically.
5. With the original matching MP4 on the demonstration host, use the [warehouse startup instructions](../README.md#getting-started) and [90-second dashboard script](../docs/demo-script.md). Play/pause/seek only for ordinary review. “Analyze new session” deliberately creates a new incident-analysis session; do not use it to restart video playback.
6. On supported NVIDIA hardware, separately show the original PipeGen graph, original speed report and generated pipeline actually running against its video input. This step remains PENDING_GPU_DEMONSTRATION until performed.

The Mac run cannot demonstrate video/box alignment without the matching MP4, physical USB hardware or a fresh TensorRT benchmark. Use existing dashboard screenshots as application evidence only. Capture original PipeGen GUI evidence directly; do not create imitation panels.
