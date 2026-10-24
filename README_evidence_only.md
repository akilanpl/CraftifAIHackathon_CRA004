## Original PipeGen Pipeline Evidence

The following are screenshots captured from the original **Hazard Zone Sentinel — Warehouse FP16 v2** project in CraftifAI PipeGen v0.5.1. They document the actual Pipeline IR, TensorRT compiler benchmark, and completed DeepStream pipeline run. Select an image to open the original full-screen capture.

### 1. Pipeline IR — seven-node graph

[![Original CraftifAI PipeGen Pipeline IR node graph, showing warehouse video input, preprocessing, YOLOv8m inference, detection postprocessing, NvDCF person tracking, restricted-zone analytics, and JSON output](evidence/pipegen-gui/warehouse-ir-graph-crop.png)](evidence/pipegen-gui/warehouse-ir-graph-original.png)

The seven nodes connect **warehouse video → preprocessing → YOLOv8m inference → postprocessing → NvDCF tracking → restricted-zone analytics → JSON output**. The [saved Pipeline IR](evidence/02-pipeline-ir/factory-PipelineIR.redacted.json) preserves its configuration.

### 2. TensorRT FP16 model speed report

[![Original PipeGen TensorRT FP16 speed report showing 6.195 ms per engine execution, 161 fps display metric, and 135.2 watts of reported GPU-board power](evidence/pipegen-gui/warehouse-fp16-benchmark-crop.png)](evidence/pipegen-gui/warehouse-fp16-benchmark-original.png)

PipeGen's on-screen benchmark presents approximately **6.195 ms per engine execution** and **135.2 W GPU-board power**. The [engine report JSON](evidence/04-tensorrt-fp16/warehouse-engine-summary.json) separately records **188.877 engine inferences/s**; both figures refer to engine benchmarks rather than full video-pipeline FPS.

### 3. DeepStream pipeline run and export

[![Original PipeGen Run Pipeline summary confirming completed warehouse video execution, 254 processed frames, and 573 detected objects across classes](evidence/pipegen-gui/warehouse-deepstream-run-crop.png)](evidence/pipegen-gui/warehouse-deepstream-run-original.png)

The original PipeGen run reports **254 processed frames in 10.12 seconds** and **573 detected objects** across classes. The [warehouse metadata audit](evidence/final-product/warehouse-audit.json) identifies **522 person observations** in the corresponding detection output, along with six tracker IDs. The [exported pipeline archive](https://github.com/akilanpl/CraftifAIHackathon_CRA004/releases/tag/warehouse-fp16-v2-2026-10-18) preserves the model, engine, and generated pipeline files.

