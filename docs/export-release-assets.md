# Preserve and package the real PipeGen export

## Read-only baseline archive audit

The genuine historical baseline archive exists at:

```text
/home/vijayababu/.pipegen/exports/pipegen-deepstream-workplace-safety-pipeline.tar.gz
```

- Size: **134,814,850 bytes** (about 128.6 MiB).
- SHA-256: `f6d0caa49fa5957d1dc2c46e76af17bea62132c1af2d9dc53c42105b74253f1a`.
- 28 archive members, 156,758,203 uncompressed file bytes.
- Includes `PipelineIR.json`, manifest, README, ONNX, FP16 engine, detector/tracker/analytics configuration and generated pipeline/parser sources.
- No absolute paths, traversal components, symbolic/hard links or credential-like member filenames were found.
- Credential-pattern screening of 19 small textual members found no matches. Binary model/engine content was not scanned, and pattern screening cannot prove all secrets absent.

See `../evidence/export-archive-audit.json`. This documentation agent inspected the archive without extracting or modifying it. The primary agent subsequently uploaded the unchanged archive to the private draft release described below. It is historical street evidence, not a factory export. The original directory remains preserved externally.

## Verified private draft asset

The primary agent verified the uploaded asset through authenticated GitHub API responses:

- Private repository: `akilanpl/hazard-zone-sentinel`; visibility unchanged.
- Draft release ID: `416346957`; tag `safety/pre-factory-40d2975`.
- [Private draft release](https://github.com/akilanpl/hazard-zone-sentinel/releases/tag/untagged-08c98dc0944deddac332).
- Asset ID: `653041956`, state `uploaded`, 134,814,850 bytes.
- API digest `sha256:f6d0caa49fa5957d1dc2c46e76af17bea62132c1af2d9dc53c42105b74253f1a` matches the local original.

This is the **historical street baseline export**, not a factory run/export. It stays out of ordinary Git history. The release remains draft; authorized repository viewers need authenticated access, and judge access/final publication must be arranged separately. Nothing here changes repository visibility. A draft asset is not proof that the hackathon submission was completed.

Name baseline and factory assets separately, for example `historical-street-pipegen-export.tar.gz` and a future `factory-pipegen-export.tar.gz`. Upload a factory archive only after its own actual run/export exists. Record its independently computed hash, media/metadata hashes, model/engine provenance, exact run ID and matching stage screenshots. Engine reuse must be labeled reuse rather than a fresh compilation/benchmark.

Before upload, review text configurations for camera URLs, paths, account names, embedded credentials and license restrictions. Retain the immutable original locally; create a separately labeled redacted distribution copy if needed and give it its own hash. Keep source media external unless redistribution is permitted and intentionally included.
