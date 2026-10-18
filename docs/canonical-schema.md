# Sentinel canonical metadata schema

This is Sentinel's internal interface. It makes no claim about the native metadata schema exported by CraftifAI PipeGen. The actual native schema must be inspected before configuring the adapter.

## Frame envelope

`POST /api/ingest/detections` accepts one frame object. See `examples/canonical-detection.json` and the authoritative Pydantic models in `backend/models.py`. Unknown canonical fields are rejected.

| Field | Requirement and meaning |
| --- | --- |
| `timestamp` | Required ISO 8601 timestamp with timezone, normalized to UTC. Use capture/event wall time, not a fabricated receipt time. |
| `camera_id` | Required stable nonempty string. Must match the camera assigned to the zone. |
| `frame_width`, `frame_height` | Required integer frame dimensions, 1–32768, describing the same coordinate frame as the boxes. |
| `detections` | Array, maximum 1000; defaults to empty. Empty frames are valid. |
| `analytics_mode` | `detections` (default) or `native`; selects exactly one event-processing path. |
| `native_events` | Array, maximum 1000; nonempty requires `analytics_mode: "native"`. |
| `source_name` | Optional actual upstream source description. Does not control incident provenance. |
| `fps`, `inference_latency_ms`, `gpu_name` | Optional genuine measured telemetry. Omit unknown values; no metrics are synthesized. |
| `video_url` | Optional supported video output URL; metadata alone does not provide live video. |

Each detection has `class_name`, numeric `confidence` in [0,1], and normalized `bbox: [x1,y1,x2,y2]`. The origin is top left; x increases right and y increases down. Coordinates must be finite and within [0,1], with x1 < x2 and y1 < y2. Coordinates are never clipped to hide invalid input. `track_id` is optional/null; integer canonical IDs convert to strings. Duplicate non-null track IDs in a frame are invalid. Only class name `person` (case insensitive) is evaluated by the engine. A missing tracking ID produces a warning and no geometry-based incident; no ID is invented.

The zone test uses the box's bottom center: `((x1+x2)/2, y2)`. The normalized polygon boundary counts as inside. A zone's confidence threshold and optional `debounce_frames` apply. Low confidence does not manufacture an exit. Absence from a frame retains previous state until the monotonic lost-track timeout, default five seconds. A confident observed foot outside clears occupancy immediately. Once state expires, a later inside observation can create a new incident; this is reacquisition, not proof of a visually observed exit. Out-of-order or repeated frame timestamps for a camera are ignored. Restarting a source with an older timestamp epoch needs a backend restart or genuinely increasing wall-clock timestamps.

## Native zone analytics

Use `analytics_mode: "native"` only when the real producer already supplies zone analytics. Native mode bypasses geometry, even when detection boxes are supplied for display. Each native event contains:

```json
{
  "event_id": "stable-upstream-event-id",
  "zone_id": "existing-sentinel-zone-id",
  "track_id": "17",
  "event_type": "zone_entry",
  "confidence": 0.94
}
```

`event_id`, `zone_id`, and `event_type` are required; event type is `zone_entry` or `zone_exit`. Confidence and track ID may be null/omitted. `zone_id` must refer to an existing Sentinel zone assigned to the envelope camera. Stable event IDs deduplicate persistently by source, camera, and event ID. If upstream IDs reset, include a genuine upstream run/session identifier in the producer's stable ID scheme; never generate a fresh ID on every retry. A repeated native entry for an already-inside known track is suppressed. Exit updates state without adding an intrusion incident; a later entry creates a new one. Without track IDs, native event IDs still protect against replay, but occupancy cannot be inferred reliably.

## Responses, provenance, and transport

Ingestion returns `{frame, incidents, warnings, status}`. A replayed/out-of-order frame returns `frame: null` with a warning. Invalid canonical payloads return 422. Genuine incident fields include ID, UTC timestamp, camera and zone IDs, zone name, optional track and confidence, event type, severity, acknowledgment state, `source`, and `synthetic`.

Live canonical input always records `source: "canonical"`. Only the configured `/api/ingest/pipegen` parser path records `source: "pipegen"`; an absent adapter returns 501. Synthetic mode records `source: "synthetic"` and `synthetic: true` and rejects the PipeGen endpoint. Payload-supplied source labels cannot override these decisions. These labels describe the selected integration path; they are not cryptographic verification that an upstream sender is genuine. Keep this local prototype's ingestion endpoints on a trusted interface.

`WS /ws/live` sends `{type, payload}` messages with types `frame`, `incident`, `status`, and `zones`. Acknowledgment sends an updated incident with the same ID; consumers should upsert by ID. JSONL exports likewise append revisions with the same ID when acknowledgment changes. REST `/api/incidents` and `/api/zones` return arrays. Source connectivity expires after the configured source timeout even while the API remains reachable.

Machine-readable contracts generated from the actual validation models: `schemas/canonical-frame.schema.json` and `schemas/zone.schema.json`. Check canonical samples without ingestion using `.venv/bin/python scripts/validate_metadata.py /actual/sample.json`.
