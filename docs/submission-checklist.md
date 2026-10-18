# Submission checklist mapped to the official problem statement

> Current consolidated evidence and Mac validation: [submission package](../submission/README.md). Historical status notes below describe earlier checkpoints; current public export access is verified in the [export manifest](../pipegen_export/manifest.json). New NVIDIA/venue execution, original PipeGen GUI captures and final organizer receipt remain pending.

Source reviewed: [official problem statement](../evidence/01-requirement-and-flow/official-problem-statement.pdf), **Embedded SF: CraftifAI Physical AI Hackathon — Official Problem Statement**, 7-page local PDF, 142,647 bytes, SHA-256 `a1da48261c91d9668e15619b40f5c93e492f40814f0921c31c831db407862966`. Full text was read and the mandatory/submission pages were visually inspected. Page references below use the PDF's physical page order.

The PDF states **4:00 pm** on page 6 without a timezone. The user explicitly selected **October 18, 2026, 4 PM IST** as the operative cutoff; earlier 6 PM instructions are superseded.

## Mandatory Track A criteria

| Official criterion | Page | Required evidence | Historical street baseline | Factory release |
| --- | --- | --- | --- | --- |
| Complete all five PipeGen stages: Requirement, Pipeline IR, Model, Compiler, Run | 2 | Actual completed stage records/configuration | Partial packaging: export contains IR/model/engine/configs; Requirement completion and stage screenshots still need confirmation | Saved Requirement/IR and new engine verified; genuine run metadata preserved; stage screenshots and live-demo proof outstanding |
| Compile at least one model to TensorRT and retain PipeGen speed report | 2 | Actual engine plus original speed report | FP16 engine preserved in the private draft export; selected measured summary is packaged, full original report/screenshot still needed | New FP16 build numeric report verified: 199 layers, 6.19475 ms engine end-to-end; actual speed-report screenshot pending |
| Execute the pipeline on NVIDIA GPU or Jetson using video file, USB/CSI camera or RTSP input | 2 | Actual GPU pipeline execution at demonstration | Genuine historical output audited; recorded dashboard replay alone is not a currently running inference pipeline | Genuine separate factory metadata snapshot verified; venue live execution and run capture still required |
| Produce an output a person/system can act on beyond detection boxes | 2 | JSON/MQTT/stream/alerts/analytics tied to actual source | Genuine metadata and 33 computed alerts verified in historical replay | Genuine factory JSON and recorded browser replay verified; 2 computed entries including 1 same-track reentry, 2 exits; native occupancy discrepancy documented |
| Make PipeGen essential to the product | 2, 7 | Explain and demonstrate real PipeGen perception driving application behavior | Source architecture and actual metadata adapter available | New factory source paired and profile READY; actual live product demonstration still required |

A video-file input is explicitly permitted by page 2. A prerecorded frontend replay of previous output does not by itself satisfy the request for the pipeline to be running on hardware at the venue (page 5).

## Submission deliverables and venue demo

- [ ] **Working prototype, page 5:** show the actual PipeGen pipeline running live on hardware at the venue. Keep the known-good baseline available while factory execution is pending.
- [ ] **Source repository, page 6:** provide accessible repository link including the PipeGen export folder. Historical export is a verified private draft asset; confirm organizer accepts that linked packaging and grant judges appropriate access. A draft private asset is not a completed submission.
- [ ] **Project description, page 6:** explain problem, Track A, inputs, tasks, models, precision and outputs; name only bonuses actually attempted/verified. The factory description must match factory evidence.
- [ ] **Evidence, page 6:** capture the actual Pipeline IR node-graph screenshot and actual TensorRT speed-report screenshot. An exported IR JSON or selected numeric summary does not replace the requested screenshots.
- [ ] **Pitch deck/video, page 6, optional:** retain the honest demo narration and recording if useful; it does not replace the working prototype.
- [ ] **Submission form, page 6:** submit through the Track A PipeGen form, https://forms.gle/eJyeCKCG2UH757QZ8 . The URL was transcribed from the official PDF; this documentation pass did not open or submit the form.
- [ ] **Setup, page 6:** verify PipeGen 0.5.1, signed-in CraftifAI account, supported NVIDIA x86-64 Linux or Jetson/JetPack 6 environment, X11 session and source access. The PDF advises keeping videos under `/home`; coordinate a supported accessible source path with the operator without changing mounts.
- [x] **Cutoff:** user selected October 18, 2026, 4 PM IST after reviewing the PDF discrepancy.

## Optional bonuses and extra user work

| Item | Official status/page | Current claim boundary |
| --- | --- | --- |
| Closed loop using PipeGen plus FirmGen to trigger a real board action | Optional bonus, 1–2 | NOT TESTED; a web alert alone is not a demonstrated firmware/physical action |
| INT8 execution **or** actual Jetson deployment, with PipeGen speed/power/accuracy trade-off report | Optional Track A bonus, 1–2 | NOT TESTED / NOT DEPLOYED; modeled Orin estimates and RTX inference do not qualify |
| Live firmware telemetry/debugging | Optional Track B bonus, 1–2 | Not a Track A mandatory requirement; NOT TESTED |
| Custom dataset, fine-tuning and held-out accuracy comparison | User-requested extension; not listed as Track A mandatory criteria | NOT TESTED until reviewed labels, splits, controlled training and actual evaluation exist |
| Factory/warehouse footage and a new matching run | User-required final product scope; not an official mandatory scene restriction | PENDING; preserve street baseline without relabeling it |

Prioritize the four mandatory Track A technical criteria and requested deliverables before optional experiments. Do not claim precision/recall/mAP from detector confidence, modeled performance or layer-matching coverage.

## Application and factory acceptance gate

- [ ] Record final backend/frontend tests, type-check and production build for this release.
- [ ] Verify HTTP/WebSocket updates, polygon CRUD, filtering, details and acknowledgment.
- [ ] Verify synthetic/live/replay/profile database separation and reconnect behavior.
- [ ] Accept the licensed factory video only after decoding, dimension/FPS/PTS checks.
- [x] Preserve genuine new factory output unchanged: immutable 254-frame metadata snapshot, verified SHA-256 and 522 person observations/6 track IDs.
- [x] Inspect saved factory ROI and generated native configuration; retain moving-camera/hypothetical screen-zone limitation. Final browser overlay check remains separate.
- [x] Bind matching hashes, source 0 and 1920×1080 dimensions in the READY factory profile; all 254 decoded frame timestamps checked with +80 ms mapping.
- [x] Verify recorded browser video/box/zone alignment at frames 25/50/75/100 (1/2/3/4 s), sampled PTS delta zero; screenshot retained. Refer to primary QA for interaction coverage.
- [x] Confirm two persisted factory event IDs and acknowledgment states survive restart; playback visualization is separate from analysis.
- [x] Retain actual app screenshot `warehouse-real-video-overlay.jpg` and metadata audit; application screenshot does not replace actual PipeGen graph/report screenshots.
- [ ] Preserve the baseline export; separately archive/hash/review the genuine factory export.
- [ ] Review source/configuration/evidence for credentials and unauthorized media before distribution.

Current factory gate: **VERIFIED RECORDED REPLAY — genuine metadata, READY profile, browser alignment and 2 persisted computed incidents verified; live venue demonstration, official PipeGen GUI screenshots and new factory export remain outstanding**. Use the immutable `../evidence/06-real-metadata/warehouse-fp16-v2-metadata.json` snapshot, not an operator output file being rewritten. Historical street evidence remains separate in `../evidence/checklist.json`; factory stages now reflect their actual verified/partial status. Artifact packaging is recorded in `../evidence/release-artifact-manifest.json`. No form submission or final release publication occurred in this documentation pass.


**Operative cutoff: October 18, 2026, 4 PM IST.** The user explicitly selected this cutoff after the PDF discrepancy was raised. Prior 6 PM assumptions are superseded.

The official form entry was browser-verified: it is a two-page feedback flow that reveals the project link on its last page. Participant feedback and the final project form/receipt remain pending. See [form handoff](submission-form-handoff.md).

Current factory checkpoint: saved Requirement and IR JSON are verified; the newly built FP16 engine and numeric timing report are verified. The official IR/speed-report GUI screenshots, full DeepStream execution, matching metadata and real warehouse application result remain pending. No JSON checkpoint or hand-authored diagram substitutes for the required screenshot.


## Final factory replay facts and limitations

Final local frontend: **http://127.0.0.1:5173**; backend: `http://127.0.0.1:8003`. Analysis: 2 observed entries including 1 same-track reentry, 0 initial-inside alerts, 2 exits and 43 suppressed holds. Native ROI occupancy disagrees with application geometry on 9 frames, cause unresolved. Camera motion and a hypothetical image-space ROI limit safety interpretation. No independent ground-truth accuracy is claimed. The captured warehouse app screenshot verifies recorded-video presentation; it does not establish a current GPU run or satisfy missing PipeGen GUI screenshots. Final regression results are recorded by the primary agent when completed.

New factory export is now available as the authenticated private prerelease asset, with matching remote/local digest. The remaining export-related gate is judge access and organizer acceptance, not archive creation. See [export delivery](export-release-assets.md).
