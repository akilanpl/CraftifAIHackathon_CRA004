# Evidence collection — pending genuine pipeline execution

Application tests and synthetic screenshots verify application behavior only. They do not prove GPU inference or PipeGen execution.

Required real artifacts:

- `pipeline-ir.png`: actual Pipeline IR screen from the completed PipeGen project.
- `tensorrt-speed-report.*`: actual PipeGen ONNX → TensorRT compilation and speed report, with FP16 settings.
- `deepstream-run.*`: working DeepStream camera/video run on the NVIDIA GPU.
- `actionable-output.json`: genuine structured incident associated with source metadata.
- `prototype-demo.*`: real outside → entry → hold → exit → re-entry demonstration.
- Actual PipeGen export in `../pipegen_export/`.

These names are suggestions, not existing evidence. Preserve timestamps and source IDs linking footage to metadata and incidents. Leave missing artifacts marked pending. Keep large footage externally and document its accessible location, without fabricating screenshots, benchmark numbers or pipeline completion.

## Application QA artifacts

`synthetic-dashboard.jpg` and `synthetic-analytics-mobile.jpg` capture the implemented UI with clearly marked synthetic test inputs. They are not real PipeGen, GPU inference, or workplace safety evidence. See `docs/verification.md` for executed checks.

## Seven-stage genuine evidence ledger

The machine-readable ledger is `checklist.json`. Every stage below is **PENDING**:

| Stage | Required genuine artifact |
| --- | --- |
| Requirement | Actual PipeGen requirement output/configuration |
| Pipeline IR | Actual Pipeline IR screenshot and export |
| Selected model/version | Real model identifier/version, provenance and ONNX details |
| TensorRT FP16 report | Actual compiler result and measured speed report |
| DeepStream execution | Actual GPU pipeline run from camera/video/stream |
| Genuine metadata | Real sample records, validated adapter and corresponding incident |
| Real-mode dashboard | UI evidence matched to the genuine source and pipeline run |

No synthetic screenshot fills any row. Do not rename synthetic QA captures to imply live or GPU evidence. Update each row only after checking the underlying genuine artifact and retain traceable source identifiers and timestamps.

`synthetic-submission-qa.jpg` documents the final historical-zone filtering and persisted acknowledgment QA. It contains only explicitly synthetic test records.

Seven numbered evidence folders now mirror the pending ledger. Their READMEs are placeholders, not completed evidence. Source video provenance is in `../demo-video/source-provenance.json`; no raw footage is included.
