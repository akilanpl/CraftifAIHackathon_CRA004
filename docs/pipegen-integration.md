# Connect genuine CraftifAI PipeGen output

## Current state

The application is integration-ready. The native PipeGen schema is unknown and its parser intentionally rejects native ingestion until configured. Neither the canonical schema nor the optional JSONL forwarding utility is a claim about CraftifAI's output format. No separate inference model is included.

## Request from the PipeGen operator

Supply these small, genuine artifacts before implementation of the native parser:

1. PipeGen version and complete exported pipeline configuration.
2. One metadata record with a tracked person outside a zone, one inside, one exit/empty frame, and any native entry analytics record.
3. Field meanings: source timestamp units/timezone, camera/source ID, source frame dimensions, bbox order and units, class representation, tracker identity and reset behavior.
4. Whether records are full frame snapshots or deltas, plus any dropped-frame/lost-track semantics.
5. Delivery transport and a sample file or documented URL; analytics event IDs and zone identifiers if present.
6. Real reported telemetry field names and units; an annotated video output URL only if actually available.

Keep source values, scrub personal information, and do not replace samples with invented structures.

## Canonical detection boundary

`POST /api/ingest/detections` accepts this application's canonical envelope. See `examples/canonical-detection.json`. Bboxes are normalized `[x1,y1,x2,y2]`, with `0 ≤ x1 < x2 ≤ 1` and the same condition on y. Coordinates refer to the full source frame. Supply `frame_width` and `frame_height` as positive original pixel dimensions. Timestamp is timezone-aware ISO 8601. `track_id` is the upstream track identifier, converted losslessly to a string. The engine uses `class_name: "person"` and bottom-center feet; confidence is a 0–1 score. Never synthesize a track ID from array position.

An outside observation of a known track establishes exit state. Empty frames do not claim an exit; an unseen track expires after the configured timeout (default 5 seconds measured with the backend monotonic clock). A later observation after expiry is treated as a fresh entry. Frames for a camera must have strictly increasing source timestamps; duplicate or older timestamps are ignored. Do not replay synthetic examples into a live database.

## Native parser implementation point

Locate `backend/adapters/pipegen_adapter.py` and replace the explicit unconfigured parsing branch only after inspecting actual metadata. Parse into the validated canonical detection model or native analytics model; preserve camera, time, confidence, external event ID and provenance. Reject ambiguous box conventions and invalid values with actionable errors. Add fixtures from sanitized genuine records and parser tests. Enable receiving status only after successful parsing.

Use detection-based zone entry or native zone-entry analytics as the authority for a camera/zone. Set `analytics_mode: "native"` for native batches: the backend does not analyze detection boxes in that batch. Keep one consistent mode for each camera/zone. Matching tracked-person occupancy suppresses duplicate entry across modes; missing native tracking IDs cannot be correlated to derived state. Reuse a stable native `event_id` on retries; generating a fresh UUID per retry defeats deduplication. Validate the native ingestion endpoint and model against the backend OpenAPI document before wiring it.

## File forwarding

The utility forwards each nonblank JSONL record without guessing its schema:

```bash
.venv/bin/python scripts/tail_ingest.py /path/to/actual-pipegen-metadata.jsonl --endpoint pipegen --follow
```

A configured upstream converter may instead write canonical records:

```bash
.venv/bin/python scripts/tail_ingest.py /path/to/canonical-metadata.jsonl --endpoint detections --follow
```

Default behavior reads existing lines. Add `--from-end` to forward only newly appended lines. The utility stops at the first invalid/rejected record and reports it; it has no durable cursor, rotation handling or automatic retry. Re-running may replay prior records, so archive input or maintain a production cursor. Follow mode waits for complete newline-terminated records. This utility is a development bridge, not a production message queue.

## Real verification sequence

Start live mode with a clean production database. Confirm no incidents before metadata arrives. Run the actual PipeGen pipeline, enter a configured polygon, and retain the raw metadata, emitted incident JSON, SQLite row and dashboard screenshot from the same event. Hold position to confirm suppression. Exit and re-enter to confirm another incident. Confirm source and timestamps remain intact. Record PipeGen's actual TensorRT compiler speed report, not timing of this API.

## Native analytics canonical envelope

The same `/api/ingest/detections` endpoint supports this application's native analytics envelope. The example below is a schema illustration only; substitute an existing zone ID and genuine upstream event identity:

```json
{
  "timestamp": "2026-10-18T12:00:00+00:00",
  "camera_id": "cam-01",
  "frame_width": 1280,
  "frame_height": 720,
  "analytics_mode": "native",
  "native_events": [{
    "event_id": "upstream-stable-event-id",
    "zone_id": "existing-sentinel-zone-id",
    "track_id": "17",
    "event_type": "zone_entry",
    "confidence": 0.94
  }]
}
```

Native `zone_exit` changes occupancy without creating an entry incident. Optional missing native track IDs remain null; stable native `event_id` still deduplicates incidents. Unknown zones or mismatched cameras are rejected. The batch timestamp must still increase on each received frame even when retrying a native event ID.

## HTTP and WebSocket reference

| Interface | Behavior |
| --- | --- |
| `GET /api/health` | Process health and selected mode |
| `GET /api/status` | Source state, available telemetry, occupancy and errors |
| `GET /api/zones` | Array of normalized zone configurations |
| `POST /api/zones` | Create `name`, `camera_id`, `polygon`, `severity`, optional confidence/debounce |
| `PUT /api/zones/{id}` | Replace configuration and reset its active track state |
| `DELETE /api/zones/{id}` | Remove configuration and reset its track state |
| `GET /api/incidents` | Incident array; optional `severity`, `zone_id`, `event_type` query filters |
| `GET /api/incidents/{id}` | Incident detail |
| `PATCH /api/incidents/{id}/acknowledge` | Body `{"acknowledged": true}` or false |
| `GET /api/analytics/summary` | Counts and daily trends from SQLite |
| `POST /api/ingest/detections` | Validated canonical detection or native batch |
| `POST /api/ingest/pipegen` | Configured native parser; otherwise explicit 501 |
| `POST /api/synthetic/step` | Explicit synthetic mode only; live mode returns 409 |
| `WS /ws/live` | JSON envelope `{"type":"status|zones|frame|incident","payload":...}` |

Use the running `/docs` OpenAPI page as the exact schema reference. Zone vertices are arrays of `[x,y]`; severity accepts `low`, `medium`, `high`, `critical`. A zone's `confidence_threshold` defaults to 0.5 and `debounce_frames` to 1. Debounce counts qualifying observations for a tracked person, not elapsed seconds. No record exists before an actual accepted entry.

## Ready-to-configure mapper and exact contract

The built-in explicit field mapper is documented in [the PipeGen handoff](pipegen-handoff.md). See [the canonical schema](canonical-schema.md), machine-readable JSON Schemas in `schemas/`, and the non-ingesting `scripts/validate_metadata.py` CLI. Native field paths remain unconfigured until genuine samples arrive.
