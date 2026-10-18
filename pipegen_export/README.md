# Original Warehouse FP16 v2 PipeGen export

The complete original pipeline, ONNX model, TensorRT FP16 engine and generated runtime artifacts are distributed in the [published GitHub prerelease](https://github.com/akilanpl/hazard-zone-sentinel/releases/tag/warehouse-fp16-v2-2026-10-18). Large binaries remain outside ordinary Git history.

| Asset | Value |
|---|---|
| Filename | `pipegen-warehouse-hazard-sentinel-pipeline.tar.gz` |
| Size | 134,818,189 bytes |
| SHA-256 | `5a2314ab3b97787ec699bb185b767bbf4ab70b7517433988d8e6d9e0c3aa4dec` |
| Engine SHA-256 | `4c11b6a4eee9274f29c55f5be92fee24357dca4d1b167b4ab5ca0ea5a4786750` |

The release is public and not a draft. The release API digest and unauthenticated download response (HTTP 200 after redirect, matching Content-Length) were verified during Mac validation. The existing [full archive audit](../evidence/factory-export-audit.json) records 28 members and the matching warehouse project/engine. The archive was not downloaded again in this pass. [Machine-readable manifest](manifest.json).

Download to a suitable artifact directory outside the repository:

```bash
curl --fail --location --output pipegen-warehouse-hazard-sentinel-pipeline.tar.gz \
  'https://github.com/akilanpl/hazard-zone-sentinel/releases/download/warehouse-fp16-v2-2026-10-18/pipegen-warehouse-hazard-sentinel-pipeline.tar.gz'
printf '%s  %s\n' \
  '5a2314ab3b97787ec699bb185b767bbf4ab70b7517433988d8e6d9e0c3aa4dec' \
  'pipegen-warehouse-hazard-sentinel-pipeline.tar.gz' | shasum -a 256 -c -
```

Inspect archive members before extracting into a new directory. The source video is external; the exported run wrapper requires an explicitly supplied `--input` path. Execution requires the supported NVIDIA/DeepStream host, not macOS. The compiled engine is an existing GPU artifact, not a portable Mac runtime.

[Five-stage provenance](../submission/five-stage-evidence.md) · [Original benchmark summary](../evidence/04-tensorrt-fp16/warehouse-engine-summary.json) · [Hardware/demo checklist](../submission/final-checklist.md).
