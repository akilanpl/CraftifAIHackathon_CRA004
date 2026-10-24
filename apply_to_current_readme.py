#!/usr/bin/env python3
"""Add the three original PipeGen screenshots to an existing README without removing its other content.
Run from the repository root after copying the evidence/pipegen-gui directory here.
"""
from pathlib import Path
import sys

repo = Path.cwd()
readme = repo / 'README.md'
if not readme.is_file():
    sys.exit('Run this script from the existing repository root: README.md not found.')
asset_names = (
    'warehouse-ir-graph-crop.png', 'warehouse-ir-graph-original.png',
    'warehouse-fp16-benchmark-crop.png', 'warehouse-fp16-benchmark-original.png',
    'warehouse-deepstream-run-crop.png', 'warehouse-deepstream-run-original.png',
)
for name in asset_names:
    path = repo / 'evidence' / 'pipegen-gui' / name
    if not path.is_file():
        sys.exit(f'Missing screenshot: {path}')

section = "## Original PipeGen Pipeline Evidence\n\nThe following are screenshots captured from the original **Hazard Zone Sentinel — Warehouse FP16 v2** project in CraftifAI PipeGen v0.5.1. They document the actual Pipeline IR, TensorRT compiler benchmark, and completed DeepStream pipeline run. Select an image to open the original full-screen capture.\n\n### 1. Pipeline IR — seven-node graph\n\n[![Original CraftifAI PipeGen Pipeline IR node graph, showing warehouse video input, preprocessing, YOLOv8m inference, detection postprocessing, NvDCF person tracking, restricted-zone analytics, and JSON output](evidence/pipegen-gui/warehouse-ir-graph-crop.png)](evidence/pipegen-gui/warehouse-ir-graph-original.png)\n\nThe seven nodes connect **warehouse video → preprocessing → YOLOv8m inference → postprocessing → NvDCF tracking → restricted-zone analytics → JSON output**. The [saved Pipeline IR](evidence/02-pipeline-ir/factory-PipelineIR.redacted.json) preserves its configuration.\n\n### 2. TensorRT FP16 model speed report\n\n[![Original PipeGen TensorRT FP16 speed report showing 6.195 ms per engine execution, 161 fps display metric, and 135.2 watts of reported GPU-board power](evidence/pipegen-gui/warehouse-fp16-benchmark-crop.png)](evidence/pipegen-gui/warehouse-fp16-benchmark-original.png)\n\nPipeGen's on-screen benchmark presents approximately **6.195 ms per engine execution** and **135.2 W GPU-board power**. The [engine report JSON](evidence/04-tensorrt-fp16/warehouse-engine-summary.json) separately records **188.877 engine inferences/s**; both figures refer to engine benchmarks rather than full video-pipeline FPS.\n\n### 3. DeepStream pipeline run and export\n\n[![Original PipeGen Run Pipeline summary confirming completed warehouse video execution, 254 processed frames, and 573 detected objects across classes](evidence/pipegen-gui/warehouse-deepstream-run-crop.png)](evidence/pipegen-gui/warehouse-deepstream-run-original.png)\n\nThe original PipeGen run reports **254 processed frames in 10.12 seconds** and **573 detected objects** across classes. The [warehouse metadata audit](evidence/final-product/warehouse-audit.json) identifies **522 person observations** in the corresponding detection output, along with six tracker IDs. The [exported pipeline archive](https://github.com/akilanpl/CraftifAIHackathon_CRA004/releases/tag/warehouse-fp16-v2-2026-10-18) preserves the model, engine, and generated pipeline files.\n\n"
text = readme.read_text(encoding='utf-8')
heading = '## Original PipeGen Pipeline Evidence'
if heading in text:
    start = text.index(heading)
    finish_candidates = [p for marker in ('\n## How It Works', '\n## Warehouse Demonstration', '\n## The Warehouse Safety Demonstration', '\n## System Architecture') if (p := text.find(marker,start+len(heading))) >= 0]
    end = min(finish_candidates) if finish_candidates else len(text)
    text = text[:start] + section.rstrip() + '\n' + text[end:].lstrip('\n')
else:
    insert_point = None
    for marker in ('## How It Works', '## The Warehouse Safety Demonstration', '## System Architecture'):
        if marker in text:
            insert_point = text.index(marker)
            break
    if insert_point is None:
        sys.exit('README structure not recognized; insert the section manually.')
    text = text[:insert_point] + section + text[insert_point:]
text = text.replace('https://github.com/akilanpl/hazard-zone-sentinel','https://github.com/akilanpl/CraftifAIHackathon_CRA004')
text = text.replace('cd hazard-zone-sentinel', 'cd CraftifAIHackathon_CRA004')
readme.write_text(text, encoding='utf-8')
print('Updated', readme, 'and linked all six image assets (3 embedded crops + 3 original captures).')
