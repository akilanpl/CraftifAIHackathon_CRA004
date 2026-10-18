"""Optional CPU-only ONNX detector. Never launches PipeGen or loads its engine."""
import hashlib
import io
import os
from pathlib import Path
import sys
import threading
import time


class InferenceUnavailable(RuntimeError):
    pass


def _sha256(path):
    value=hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''):value.update(chunk)
    return value.hexdigest()


class IndependentDetector:
    def __init__(self,model_path=None,dependencies_path=None,confidence=0.0):
        self.model_path=Path(model_path or os.getenv('SENTINEL_AI_MODEL_PATH','')) if model_path or os.getenv('SENTINEL_AI_MODEL_PATH') else None
        self.dependencies_path=dependencies_path or os.getenv('SENTINEL_AI_DEPENDENCIES_PATH','')
        self.confidence=confidence
        self._session=None;self._lock=threading.Lock();self.model_sha256=None;self._error=None

    def _load(self):
        if self._session is not None:return
        with self._lock:
            if self._session is not None:return
            if self.model_path is None or not self.model_path.is_file():
                raise InferenceUnavailable('Independent ONNX model is not configured. Run the separate host setup; Warehouse V2 remains available.')
            for entry in self.dependencies_path.split(os.pathsep):
                if entry and entry not in sys.path:sys.path.append(entry)
            try:
                import numpy as np
                import onnxruntime as ort
                from PIL import Image
            except ImportError as exc:
                raise InferenceUnavailable('Independent CPU inference dependencies are unavailable; run scripts/setup-independent-ai-host.sh on the host.') from exc
            try:
                options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
                options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
                session=ort.InferenceSession(str(self.model_path),sess_options=options,providers=['CPUExecutionProvider'])
                inputs=session.get_inputs()
                if len(inputs)!=1 or len(inputs[0].shape)!=4 or inputs[0].shape[0]!=1 or inputs[0].shape[1]!=3 or inputs[0].type!='tensor(float)':
                    raise ValueError('Expected a batch-one NCHW float32 YOLOv8 ONNX model')
                height,width=inputs[0].shape[2:]
                if not isinstance(height,int) or not isinstance(width,int) or not 32<=min(height,width)<=max(height,width)<=2048:
                    raise ValueError('Explicit supported static model dimensions are required')
                if session.get_providers()!=['CPUExecutionProvider']:
                    raise ValueError('Only CPU execution is permitted for this independent worker')
                self._np,self._Image,self._ort=np,Image,ort
                self.input_name=inputs[0].name;self.height,self.width=height,width
                self.model_sha256=_sha256(self.model_path)
                self._session=session
            except Exception as exc:
                self._error='Independent ONNX model could not be loaded by the CPU runtime; inspect the host setup and model compatibility.'
                raise InferenceUnavailable(self._error) from exc

    def status(self):
        try:self._load()
        except InferenceUnavailable as exc:return dict(available=False,engine='onnxruntime_cpu',reason=str(exc),physical_camera_hardware_test='NOT TESTED')
        return dict(available=True,engine='onnxruntime_cpu',runtime_version=self._ort.__version__,providers=['CPUExecutionProvider'],model='YOLOv8m ONNX',model_sha256=self.model_sha256,input_shape=[1,3,self.height,self.width],physical_camera_hardware_test='NOT TESTED')

    def detect(self,jpeg_bytes):
        self._load();started=time.perf_counter();np,Image=self._np,self._Image
        try:
            with Image.open(io.BytesIO(jpeg_bytes)) as source:
                if source.format!='JPEG':raise ValueError('Only JPEG frames are supported')
                width,height=source.size
                if width<16 or height<16 or width*height>4096*4096:raise ValueError('Frame dimensions exceed supported limits')
                image=source.convert('RGB')
        except Exception as exc:raise ValueError('Invalid or unsupported JPEG frame') from exc
        scale=min(self.width/width,self.height/height)
        resized_w,resized_h=round(width*scale),round(height*scale)
        pad_x,pad_y=(self.width-resized_w)//2,(self.height-resized_h)//2
        canvas=Image.new('RGB',(self.width,self.height),(114,114,114));canvas.paste(image.resize((resized_w,resized_h),Image.Resampling.BILINEAR),(pad_x,pad_y))
        tensor=np.asarray(canvas,dtype=np.float32).transpose(2,0,1)[None]/255.
        output=self._session.run(None,{self.input_name:tensor})[0]
        detections=decode_yolov8(output,width,height,self.width,self.height,resized_w/width,resized_h/height,pad_x,pad_y,self.confidence,np)
        elapsed=(time.perf_counter()-started)*1000
        return dict(width=width,height=height,detections=detections,processing_latency_ms=elapsed,processing_fps=1000/elapsed,model_sha256=self.model_sha256,engine='onnxruntime_cpu',runtime_version=self._ort.__version__,provenance='independent_ai_inference')


def decode_yolov8(output,width,height,input_width,input_height,scale_x,scale_y,pad_x,pad_y,threshold,np):
    """YOLOv8 raw xywh + 80 class scores, person class0, explicit NMS."""
    data=np.asarray(output)
    if data.ndim!=3 or data.shape[0]!=1:raise InferenceUnavailable('Unsupported ONNX output shape')
    data=data[0]
    if data.shape[0]==84:data=data.T
    if data.ndim!=2 or data.shape[1]!=84 or data.shape[0]>100000:raise InferenceUnavailable('Expected YOLOv8 raw output with80class scores')
    finite=np.isfinite(data).all(axis=1);scores=data[:,4:];classes=scores.argmax(axis=1)
    candidates=data[finite&(classes==0)&(scores[:,0]>=threshold)]
    candidates=candidates[np.argsort(-candidates[:,4])[:1000]]
    boxes=[]
    for row in candidates:
        cx,cy,bw,bh=[float(x) for x in row[:4]]
        x1=max(0.,min(1.,(cx-bw/2-pad_x)/scale_x/width));y1=max(0.,min(1.,(cy-bh/2-pad_y)/scale_y/height))
        x2=max(0.,min(1.,(cx+bw/2-pad_x)/scale_x/width));y2=max(0.,min(1.,(cy+bh/2-pad_y)/scale_y/height))
        if x2<=x1 or y2<=y1:continue
        box=[x1,y1,x2,y2]
        if any(_iou(box,prior['bbox'])>.45 for prior in boxes):continue
        boxes.append(dict(bbox=box,class_name='person',confidence=float(row[4])))
        if len(boxes)>=100:break
    return boxes


def _iou(a,b):
    overlap=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    area=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-overlap
    return overlap/area if area>0 else 0.
