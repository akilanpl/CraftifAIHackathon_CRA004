# Genuine PipeGen handoff

**Update:** the actual `video_json_export` batch is now supported by the dedicated recorded replay adapter. See [real PipeGen replay](real-pipegen-replay.md). The strict wall-clock requirements below still apply to live ingestion; replay explicitly uses relative PTS and a labeled session clock. No capture UTC is inferred.


The dashboard, event engine, database, API, and configurable metadata mapper are integration-ready. This repository has not run PipeGen, compiled TensorRT, measured GPU inference, or supplied judging evidence. CraftifAI PipeGen remains the required actual vision pipeline.

## What the PipeGen operator must supply

Provide a small **genuine, unmodified** JSON/JSONL sample containing at least:

1. A frame with a tracked person outside, a subsequent entry, repeated inside frames, an observed exit, and a reentry. Include empty frames and multiple tracked people if supported.
2. The capture timestamp definition and units: timezone-bearing ISO wall time or Unix epoch s/ms/us/ns. Pipeline running time, frame sequence, and monotonic PTS are insufficient without a verified wall-clock conversion.
3. Exact frame width/height and which frame the coordinates describe, including resizing, padding, cropping, rotation, or letterboxing. Mapping currently assumes boxes already refer to the configured frame; a verified custom parser must undo additional transforms.
4. Exact bounding-box units and order: normalized or absolute pixels; `[x1,y1,x2,y2]` or `[x,y,width,height]`. For object-shaped boxes, identify all four fields.
5. The camera identifier, person class label or numeric class map, confidence scale, tracker ID type and missing-ID sentinel, plus tracker ID reuse/reset behavior.
6. If native analytics exists: real event type, stable unique event ID, zone identifier, track ID, entry/exit examples, confidence availability, and replay/retry behavior. Match native zone IDs to Sentinel zone IDs explicitly.
7. Transport details: one JSON object per frame or a batch, output file/socket/topic, sample export location, update cadence, and whether a supported annotated video URL exists.
8. Actual telemetry field definitions where available, plus actual Pipeline IR, TensorRT speed report, DeepStream run evidence, and PipeGen export for submission.

Do not substitute the artificial adapter fixture for genuine output. `examples/field-mapping.artificial-input.json` and `examples/field-mapping.example.json` are deliberately invented mapping tests, **not PipeGen schemas or hackathon evidence**.

## Configure only verified fields

`backend/adapters/field_mapping.py` provides a parser callable for explicit mappings. It makes no discovery guesses. Copy the example to a local mapping file and replace every path after inspecting the genuine sample.

A field reference is exactly one of `{"path":"/nested/key"}` or `{"value":"explicit constant"}`. Paths are JSON Pointers: `/` separates object keys or explicit array indexes; `~1` escapes `/` and `~0` escapes `~`. No wildcards or automatic aliases exist. Frame fields are relative to the root object. Detection and native event fields are relative to each collection element. Constants are appropriate only for verified static facts, such as a fixed camera name or frame dimensions.

Required mapping fields are `version: 1`, timestamp reference, timestamp format, camera reference, width/height references, and `analytics_mode`. Detection mode requires a `detections` object containing `list_path`, `class_name`, `confidence`, and `bbox`; `track_id` is optional. Numeric classes require an explicit `class_map`, for example `{"0":"person","2":"forklift"}`. Unknown mapped classes fail closed; include every actual class or filter at a verified custom adapter. Confidence must already be numeric [0,1]; percentages require an explicit custom conversion, not a guess.

Bounding-box configuration requires both `format: "xyxy" | "xywh"` and `units: "pixels" | "normalized"`. Select exactly one of:

```json
{"path":"/rectangle","format":"xywh","units":"pixels"}
```

or four ordered references for object coordinates:

```json
{
  "components": [
    {"path":"/rectangle/left"}, {"path":"/rectangle/top"},
    {"path":"/rectangle/width"}, {"path":"/rectangle/height"}
  ],
  "format":"xywh", "units":"pixels"
}
```

Pixel coordinates divide by the verified frame dimensions. There is no clipping, guessed axis order, inferred scale, invented tracker, or fabricated timestamp. Missing/null configured tracking IDs remain null. Optional `missing_track_values`, such as `[-1]`, must be set from real tracker documentation; IDs such as zero and minus one are otherwise preserved. Malformed or missing required paths reject the whole frame. An empty collection is valid; a missing collection is not treated as empty.

Timestamp formats are `iso8601`, `epoch_s`, `epoch_ms`, `epoch_us`, or `epoch_ns`. ISO requires a timezone. Epoch conversion uses explicit units and decimal arithmetic, accepts numbers or numeric strings, and normalizes UTC. Nanoseconds truncate to Python's microsecond precision; upstream rates must not produce identical resulting timestamps for distinct frames. Naive times, NaN, infinities, and out-of-range dates fail validation.

Optional frame-level telemetry references are `source_name`, `fps`, `inference_latency_ms`, `gpu_name`, and `video_url`. Omit unreported telemetry entirely. A configured telemetry path is required to exist; the mapper does not invent fallback values.

Native mode requires only `native_events`, with `list_path`, `event_id`, `zone_id`, and `event_type` references; optional fields are `track_id`, `confidence`, `missing_track_values`, and `event_type_map`. Example event type map: `{"ENTER":"zone_entry","EXIT":"zone_exit"}`. Native collection and detection mapping cannot both be active. Mapping alone does not create zones or translate mismatching zone IDs; configure verified constants or use a custom parser when IDs need translation. See [canonical schema](canonical-schema.md) for deduplication and occupancy semantics.

## Switch from synthetic to genuine input

Stop the synthetic backend. Keep its database as test-only evidence. Start a fresh live backend with a separate live SQLite file and a reviewed mapping, from the repository root:

```bash
export SENTINEL_MODE=live
export SENTINEL_DB_PATH="$PWD/data/sentinel.sqlite3"
export SENTINEL_PIPEGEN_PARSER=backend.adapters.field_mapping:parse
export SENTINEL_FIELD_MAPPING="$PWD/config/local-pipegen-mapping.json"
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Create real camera zones in the dashboard before ingesting; the live database starts without synthetic starter zones. Point the existing JSONL tail utility at actual emitted metadata, using `/api/ingest/pipegen` as its destination. For a single genuine sample:

```bash
curl --fail-with-body -H 'Content-Type: application/json' \
  --data-binary @/path/to/genuine-frame.json \
  http://127.0.0.1:8000/api/ingest/pipegen
```

This parser caches the reviewed mapping per process. Restart after changing the mapping. No parser configured returns 501. Missing/bad mapping or rejected metadata produces a non-success response, with no fabricated incident. The backend marks this integration path `pipegen`; the operator remains responsible for ensuring it receives actual PipeGen output. Do not post synthetic fixtures to a live integration endpoint.

Confirm returned normalized boxes, camera, UTC timestamp, and track IDs against the real source before testing entry/hold/exit/reentry. Check one incident per actual entry, live WebSocket updates, acknowledgment persistence, and correct source disconnection on a paused producer. Preserve genuine received metadata and resulting actionable incident JSON alongside the official evidence files.

If genuine metadata cannot fit the explicit mapper (batched streams, geometry transforms, native ID translation, unusual timestamps), implement a verified `module:callable` parser following `backend/adapters/pipegen_adapter.py`. Never force an incorrect mapping merely to show a connected state.

## Validate before sending

Run `.venv/bin/python scripts/validate_metadata.py /actual/genuine-record.json --mapping /actual/reviewed-mapping.json` to inspect the normalized result without network calls or database writes. Schema files are in `schemas/`. Browser video must be a browser-playable HTTP(S) output; a raw RTSP URL needs a compatible gateway and is not directly playable by the dashboard video element.
