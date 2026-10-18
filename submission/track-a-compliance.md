# Track A compliance

Source: [official problem statement](../evidence/01-requirement-and-flow/official-problem-statement.pdf), mandatory requirements on page 2, submission evidence on pages 5–6, judging on page 7.

| Requirement | Verified evidence | Remaining proof |
|---|---|---|
| Full Requirement → Pipeline IR → Model → Compiler → Run | Saved Requirement/IR, model references, compiled-engine summary, archive audit and genuine recorded output. [Five-stage record](five-stage-evidence.md). | Original stage/node-graph GUI captures: PENDING_GUI_CAPTURE. |
| TensorRT model and PipeGen speed report | Existing FP16 compiler/engine measurements and engine in the [published export](../pipegen_export/README.md). | Original PipeGen speed-report screenshot: PENDING_GUI_CAPTURE. Existing dashboard screenshots are application evidence. |
| NVIDIA hardware run on a permitted input | Genuine previous warehouse MP4 processing preserved as frame-stamped output. Video-file input is explicitly permitted. | New NVIDIA/venue demonstration: PENDING_GPU_DEMONSTRATION. Mac replay does not satisfy this physical execution proof. |
| Actionable output beyond boxes | JSON → application zone decisions → two persisted entries → WebSockets, review, acknowledgment and analytics. [New Mac verification](mac-validation.md). | Current hardware demonstration of the complete chain. |

PipeGen is load-bearing: the core warehouse demonstration consumes its genuine person/tracking output. The independent CPU monitor is an additional path, not a substitute for PipeGen. No INT8, Jetson or FirmGen bonus is claimed.
