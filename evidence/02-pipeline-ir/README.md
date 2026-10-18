# Genuine saved factory Pipeline IR — screenshot pending

`factory-PipelineIR.redacted.json` is a sanitized copy of the actual saved IR for **Hazard Zone Sentinel — Warehouse FP16 v2**, project `5b159399-c172-4ac5-8b45-430bd54a4a99`. It contains seven nodes and ten connections:

1. Warehouse video-file input: 1920 × 1080, 25 FPS.
2. RGB normalization and resize to 640 × 480, tensor `[1,3,480,640]`.
3. Requested pretrained YOLOv8m ONNX inference, described as TensorRT FP16.
4. Person decoding/filtering, confidence threshold 0.5.
5. Native DeepStream NvDCF person tracking configuration.
6. Restricted-zone entry/occupancy processing with normalized polygon `[(0.42,0.74),(0.62,0.74),(0.62,0.86),(0.42,0.86)]`.
7. JSON output.

These are **saved configuration and pseudocode**, not proof that the described nodes executed. The FP32 input/output tensor declarations in the IR do not by themselves establish engine internal precision. No model compilation, benchmark, execution or factory detections are claimed from this file.

The original IR SHA-256 is `b58bbe4457e21e80de4c3e973f7c860af5e4b6dfb94a3efcd1bb3733e49e1e77`. The distributed redacted hash and source/checkpoint comparison are recorded in `../01-requirement-and-flow/factory-checkpoint-manifest.json`. Account/home-path identifiers were substituted while retaining graph topology, tensor shapes, source filename and polygon.

**Official Pipeline IR node-graph screenshot: PENDING ACTUAL PIPEGEN GUI CAPTURE.** The exported JSON supports provenance but does not replace the screenshot requested by the official submission rules. No screenshot was fabricated.
