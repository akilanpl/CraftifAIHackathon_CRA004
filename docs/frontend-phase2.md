# Phase 2: model evidence, analytics and zone workspace

This change extends the existing light workspace to Model Performance, Analytics and Zone Management. Overview, Recorded Monitoring and Incident Center retain their released layout. AI Camera Monitor and Integration retain their existing feature implementations.

## Evidence scope

The model page loads committed evidence JSON rather than reproducing screenshot numbers. The original Warehouse V2 `compile.data.json` and `engine.data.json` hashes were checked read-only against the summary's source hashes. Engine size is **52,792,260 bytes** (52.79226 decimal MB); the supplied reference incorrectly shows 5,279,280 bytes. Reported GPU-board power is **135.222 W**, 66 samples, reported accuracy **±5 W**, using nvidia-smi during the engine run. It was not independently remeasured. The reference's ±2 W is incorrect.

GPU compute **5.28244 ms**, end-to-end engine **6.19475 ms**, and reported engine throughput **188.877 inferences/s** describe distinct measurements. An inverse latency calculation is not substituted for reported throughput. The benchmark device is unidentified; modeled Orin NX estimates do not verify a Jetson deployment. Historical engine evidence remains separate from Warehouse V2 and CPU inference. Downloadable source JSON and copy actions expose provenance.

Independent accuracy remains **PENDING HUMAN REVIEW**. INT8 execution, Jetson deployment, physical USB hardware and FirmGen closed-loop hardware remain **NOT TESTED**. Replay speed is not inference throughput, CPU inference is not TensorRT execution, and model-only reports do not measure full-pipeline performance or whole-system power.

## Analytics semantics

All charts use persisted API aggregates. UTC daily buckets can be grouped into Monday-starting UTC weeks without inventing intervening incidents. Stored incidents, current analysis occupancy, current analysis session alerts, and transient video overlays remain distinct. Historical dates are preserved. Acknowledgment totals refresh through the existing API/WebSocket flow. Empty databases render empty states.

## Zone safety

Zone selection creates a separate editable draft. Cancel discards only that draft. Explicit save calls the existing application API; it does not modify original exported DeepStream ROI configuration. Normalized coordinates remain within 0–1. Polygon validation rejects degenerate/intersecting shapes. Destructive actions require confirmation. CRUD browser acceptance uses only the isolated QA database, never the production Warehouse V2 database.

The moving-camera V2 polygon remains a screen-relative demonstration region, not a calibrated physical safety boundary.

## Reproduce checks

Use the existing setup and launch commands in the README. Run `bash scripts/check.sh` with the documented opt-in AI integration environment for actual local CPU-worker tests. Source files, test logs, screenshots, API checks and integrity observations for this change are under `evidence/ui-phase2/`.
