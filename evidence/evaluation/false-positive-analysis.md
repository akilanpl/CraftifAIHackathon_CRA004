# Qualitative shelving candidate — human review pending

The genuine CPU evaluation processed 41 real warehouse JPEG frames. Frame 106 is at media 4.24 s / original PTS 4.32 s. The original ONNX model emitted a person candidate with normalized xyxy `[0.7597975731, 0.1914931827, 0.9993304253, 0.9873859406]`, confidence **0.5661550760**. Visual AI-assisted inspection places it over right-side shelving/background rather than a visible worker. This is a qualitative observation, not an independently human-approved false-positive label or an accuracy metric.

The candidate survives confidence thresholds 0.25, 0.40 and 0.50; it is filtered at 0.60 and 0.70. Three visible-worker candidates in this frame scored above 0.91. This one frame cannot establish whether higher thresholds miss people elsewhere. Production confidence remains **0.50 unchanged**.

Across all 41 frames, retained candidate counts at 0.25/0.40/0.50/0.60/0.70 are **94/88/82/80/80**. The detector records up to 100 post-NMS person candidates per frame at a confidence floor of zero (4,100 raw candidates total). Filtered candidates are not confirmed false positives. Ground-truth counts, TP/FP/FN, precision, recall, F1, AP50 and mAP50:95 remain **PENDING HUMAN REVIEW**.

Independent manual labels are drawn with predictions hidden. Do not use this qualitative analysis to auto-fill annotations. The source is one short moving-camera clip and does not represent deployment diversity. The 960×540 JPEG review images are the exact images inferred for this experiment; results do not measure original full-resolution video accuracy.
