"""Optional real-runtime decoder regression checks; no model predictions are GT."""
import os
from pathlib import Path
import pytest
from backend.independent_inference import IndependentDetector,InferenceUnavailable,decode_yolov8


def test_unconfigured_model_has_explicit_unavailability(tmp_path):
    assert not IndependentDetector(tmp_path/'missing.onnx').status()['available']


def numpy_runtime():
    import sys
    external=os.getenv('SENTINEL_AI_DEPENDENCIES_PATH','/mnt/seagate4/PipeGenHackathon/independent-ai-monitor/dependencies')
    if Path(external).is_dir() and external not in sys.path:sys.path.append(external)
    return pytest.importorskip('numpy')


def test_raw_yolov8_decode_letterbox_class_filter_and_nms():
    np=numpy_runtime();raw=np.zeros((1,84,4),dtype=np.float32)
    # 960x540 -> 640x360 +60 vertical padding inside static 640x480 input.
    raw[0,:4,0]=[320,240,320,180];raw[0,4,0]=.9
    raw[0,:4,1]=[321,241,320,180];raw[0,4,1]=.8  # duplicate suppressed
    raw[0,:4,2]=[100,100,30,30];raw[0,5,2]=.99  # non-person
    raw[0,:4,3]=[100,100,30,30];raw[0,4,3]=float('nan')
    boxes=decode_yolov8(raw,960,540,640,480,2/3,2/3,0,60,.5,np)
    assert len(boxes)==1
    assert boxes[0]['bbox']==pytest.approx([.25,.25,.75,.75])
    assert boxes[0]['confidence']==pytest.approx(.9)
    transposed=decode_yolov8(raw.transpose(0,2,1),960,540,640,480,2/3,2/3,0,60,.5,np)
    assert transposed==boxes
    with pytest.raises(InferenceUnavailable):decode_yolov8(np.zeros((1,6,4)),960,540,640,480,1,1,0,0,.5,np)


def test_optional_genuine_cpu_model_rejects_non_jpeg():
    model=os.getenv('SENTINEL_AI_MODEL_PATH')
    if not model:pytest.skip('Configure external CPU runtime/model to exercise real model loading')
    detector=IndependentDetector(model,os.getenv('SENTINEL_AI_DEPENDENCIES_PATH',''))
    assert detector.status()['available']
    with pytest.raises(ValueError):detector.detect(b'not a jpeg')
