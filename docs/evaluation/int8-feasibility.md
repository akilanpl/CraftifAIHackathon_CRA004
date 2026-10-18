# INT8 feasibility and bonus evidence audit

## Decision

**Technical: conditional GO for a future, separately named TensorRT INT8 candidate on the RTX 2060 SUPER. Execution now: NO-GO in this audit. Bonus status: NOT TESTED / NOT CLAIMED.** This distinction is deliberate: supported hardware does not establish a calibrated, compatible, accurate or faster engine. This workstream authorizes read-only inspection/documentation, not compilation, quantization, GPU workloads, container access or PipeGen changes. The working FP16 engine and V2 remain preserved.

The inspection used the isolated `feature/ai-evaluation-and-release-audit` worktree. Only this document and `../../evidence/evaluation/int8-feasibility.json` were authored. No tools, models or datasets were downloaded or installed; no engine was loaded or rebuilt.

## Official criteria and what qualifies

The local [official statement](../../evidence/01-requirement-and-flow/official-problem-statement.pdf) was read in full (7 pages; SHA-256 `a1da48261c91d9668e15619b40f5c93e492f40814f0921c31c831db407862966`). Page 2 makes the five PipeGen stages, a TensorRT engine with PipeGen speed report, actual GPU pipeline execution and actionable output mandatory. FP16 can satisfy the precision aspect of that mandatory engine requirement; INT8 is not mandatory.

The optional Track A Edge Optimization bonus requires **running INT8 or deploying on a Jetson**, with the speed, power and accuracy trade-off reported through PipeGen (pages 1–2). Independent ONNX Runtime CPU quantization or inference would be a separate application experiment; it does not establish that bonus. A newly built standalone TensorRT INT8 file alone would also leave actual PipeGen integration/run/report evidence outstanding. The project must keep PipeGen essential (pages 2 and 7).

Jetson: **NOT DEPLOYED / NOT TESTED**. Modeled Orin profiles are not a device run. Closed loop: **NOT TESTED**; pages 1–2 require a perception event to drive real FirmGen board action, not a web acknowledgment. Physical USB hardware is also NOT TESTED, separately from these bonuses.

## Technical basis and version limits

NVIDIA identifies the RTX 2060 SUPER as Turing. NVIDIA's Turing guide identifies the architecture with compute capability 7.5 and describes 8-bit integer Tensor Core matrix operations. This supports an architectural feasibility conclusion, not a measured speedup or proof that every YOLO layer will use INT8. [RTX 2060 SUPER specifications](https://www.nvidia.com/content/nvidiaGDC/gb/en_GB/geforce/graphics-cards/rtx-2060-super.html), [Turing tuning guide](https://docs.nvidia.com/cuda/archive/12.6.0/turing-tuning-guide/index.html).

The existing engine reports TensorRT **10.3.0**. Its developer guide distinguishes implicit INT8 using calibration/scales from explicit quantization encoded as Q/DQ nodes in the model. Either candidate route must match the actual supported exporter/parser and build environment. [TensorRT 10.3 developer guide, table on printed page 55](https://docs.nvidia.com/deeplearning/tensorrt/archives/tensorrt-1030/pdf/TensorRT-Developer-Guide.pdf). The precise PDF table was available through NVIDIA's indexed text; direct opening failed and archived HTML links redirected to current docs.

Do not apply newer-version recipes blindly: NVIDIA's migration guidance states that TensorRT 11 removes the legacy calibrator APIs; that is not evidence those APIs were absent in the existing 10.3 environment. No runtime upgrade is proposed. [NVIDIA 10.x-to-11.x migration](https://docs.nvidia.com/deeplearning/tensorrt/latest/api/migration/tensorrt-10x-to-11x-python-api-patterns.html).

NVIDIA requires representative inputs for calibration and notes that sample requirements are application-dependent. A short single warehouse video alone is not demonstrated calibration diversity or held-out quality evidence. [NVIDIA quantized types/calibration](https://docs.nvidia.com/deeplearning/tensorrt/10.x.x/inference-library/work-quantized-types.html). NVIDIA also warns that an INT8 `trtexec` build without a supplied calibration cache can assign random dynamic ranges and yield unsuitable accuracy; a successful command is not calibrated detection validation. [TensorRT 10.1 developer guide, trtexec appendix](https://docs.nvidia.com/deeplearning/tensorrt/archives/tensorrt-1010/pdf/TensorRT-Developer-Guide.pdf). That nearby-version warning is not presented as a new 10.3 execution result.

## Existing artifacts and measurements

| Artifact | Verified fact | Limitation |
| --- | --- | --- |
| Exported YOLOv8m ONNX | 103,767,487 bytes; independently streamed SHA-256 `8db1e3bb5e53410eb79da1e166fa3e1a05d6d1ff29df33af7345f2f3b73e20d7` | No structural Q/DQ graph analysis performed here; no INT8 model claimed |
| Factory FP16 engine summary | 52,792,260 bytes; 199 layers, 185 FP16 + 14 FP32; engine hash `4c11b6a4eee9274f29c55f5be92fee24357dca4d1b167b4ab5ca0ea5a4786750`; input `[1,3,480,640]` | FP16 label does not mean every layer is FP16; not an INT8 plan |
| Existing factory engine timing | 5.28244 ms measured GPU compute, 6.19475 ms end-to-end engine timing; reported throughput 188.877 QPS | Distinct metrics; do not replace throughput with an arbitrary reciprocal or call either full DeepStream FPS. Reported measured-device field is unidentified |
| Existing reported power | 135.222 W engine-run GPU-board report, nvidia-smi source, 66 samples, min 22.63/max 153.91 W, stated accuracy 5 W | Previously captured report; not independently remeasured here, not CPU/whole-system/DeepStream power |
| Orin estimate in report | Modeled profile retained separately | Not measured Jetson speed/power, hardware deployment or an INT8 result |
| INT8 plan/calibration/cache | None located in scoped searches | Absence in searched locations does not prove none exists elsewhere |

Primary report: `../../evidence/04-tensorrt-fp16/warehouse-engine-summary.json`. Original compile/engine JSON was inspected read-only; `reconcile.calibrated=false` is a modeling reconciliation setting, **not proof about INT8 calibration data**. The source ONNX and FP16 plan remain external in the existing warehouse export. No originals were changed or copied.

## Current execution gates

- `trtexec` and `nvcc` were not found on this host PATH or in the scoped `/usr`, `/usr/local`, `/opt`, external storage searches. Existing reports demonstrate a prior TensorRT environment, not a currently usable host builder. Container tools were not inspected or launched.
- A read-only `nvidia-smi` identity/memory query could not communicate with the driver from this sandbox. Current GPU availability/VRAM is **unverified here**; do not diagnose a broken host driver or change it from this result.
- Disk snapshot: root **1,443,016,704 bytes free**, external ext4 **41,311,166,464 bytes free**. They exceed the 1 GiB/20 GiB thresholds, but root margin is only about 352 MiB. This was `df`, not a new successful storage-guard write probe; current host guard, RAM, VRAM and peak build workspace must be checked before an authorized future experiment. No extra model/framework/runtime download is justified by this audit.
- The independent application's discovered dependency directory includes ONNX Runtime CPU, not an identified host TensorRT/Model Optimizer installation. No new installation was attempted.
- No calibrated INT8 candidate, representative calibration manifest, independent held-out accuracy comparison or matched FP16/INT8 speed/power experiment is supplied. The existing moving-camera demo and nine native-ROI disagreements cannot substitute for labeled ground truth.

## Conditional future experiment, after explicit authorization

1. Preserve original hashes and place a separately named candidate, calibration files and reports on approved external storage. Never overwrite the working FP16 plan, source ONNX, project or V2 database. Recheck the storage guard and available CPU RAM/GPU memory before starting.
2. Verify the actual supported TensorRT 10.3 builder and PipeGen INT8 import/calibration route. Do not infer PipeGen support from generic TensorRT capability. A separate candidate project/version and saved export should retain provenance and the compatible detector parser.
3. Define representative, licensed calibration inputs with recorded source hashes, sampling policy and exact deployed preprocessing/tensor shape. Keep calibration separate from an independently reviewed evaluation split by source/scene. Calibration input need not be labeled, but accuracy evaluation does. Predictions are not independent labels. Do not transplant scales across models/releases without validation.
4. Either create an explicitly quantized Q/DQ ONNX copy using a verified compatible tool, or use the supported 10.3 implicit calibration route with a genuine calibration cache. No random scales/cache substitution. Inspect actual layer precision/fallbacks and record input/output/class compatibility, rather than treating the INT8 flag/name as proof.
5. On the same RTX device and controlled workload, warm up and repeat matched FP16/INT8 measurements: identical source, shape/batch, preprocessing/postprocessing, thresholds, software, transfer settings and concurrency. Record latency distributions, throughput, engine size and GPU-board power with scope. Avoid concurrent inference/training/dashboard work that invalidates comparison. Speedup or power reduction is a hypothesis until measured.
6. Evaluate both candidates on the same held-out person boxes and separately labeled entry/exit events; report FP/FN, precision/recall/F1 and supported mAP, thresholds, sample size and scene limits. Include known shelving false positives and approximate IoU tracking limitations. A failed/regressed candidate remains separate; retain FP16.
7. For the actual bonus, run the accepted INT8 candidate through PipeGen/DeepStream and retain its actual speed/power/accuracy reports, stage screenshot evidence and actionable output. A CPU ONNX experiment must stay labeled independent and cannot fill these slots.

No executable build/quantization command is included as an implied authorization to run it now.

## Submission/evidence availability for the release audit

The worktree contains the official PDF, saved redacted Requirement/IR JSON, factory engine numeric summary, generated analytics configuration, immutable 254-frame factory metadata, application overlay screenshots, independent CPU source reports and a hashed genuine factory-export audit. These are real artifacts, each with its own scope.

No actual PipeGen node-graph GUI screenshot or actual PipeGen speed-report GUI screenshot is present in the scoped stage directories. `warehouse-engine-performance.jpg` is an **application performance view**, not a substitute for those organizer-requested screenshots. A local full export exists and has an audit; historical release manifests describe asset distribution but do not attest current release visibility or judge access. This read-only workstream did not query/change GitHub.

The form handoff still records participant feedback/final project link and submission receipt as pending; `evidence/checklist.json` has `submitted: false` and `receipt: null`, and no receipt/confirmation artifact was located. Do not claim final submission. The official page-6 URL is a feedback entry flow; live venue GPU demonstration and required screenshots remain distinct from recorded downstream replay. These inconsistencies/gaps are reported for the parent README/release audit, without editing shared evidence.
