#!/usr/bin/env python3
"""CPU decode + real independent HTTP inference smoke. Requires system PyGObject/GStreamer.
No PipeGen metadata is read. Original video is read-only; reports are written explicitly.
"""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import urllib.request
import gi

gi.require_version('Gst','1.0')
from gi.repository import Gst


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video',required=True,type=Path)
    parser.add_argument('--api',default='http://127.0.0.1:8004/api/ai')
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    def call(path,data=None,method=None,kind='application/json'):
        body=data if isinstance(data,bytes) else json.dumps(data).encode() if data is not None else None
        with urllib.request.urlopen(urllib.request.Request(args.api+path,data=body,headers={'Content-Type':kind},method=method),timeout=30) as response:return json.load(response)
    status=call('/status')
    if not status['inference']['available']:raise SystemExit('Real independent inference is unavailable; no simulation fallback permitted')
    video=args.video.resolve(strict=True)
    config=dict(source_type='virtual_video',name='Genuine decoded video verification',polygon=[[.55,.45],[.95,.45],[.95,.95],[.55,.95]],confidence_threshold=.5)
    session=call('/sessions',config);identifier=session['id'];rows=[]
    Gst.init(None)
    pipeline=Gst.parse_launch('filesrc name=input ! qtdemux ! h264parse ! avdec_h264 ! videoconvert ! videoscale ! video/x-raw,width=960,height=540 ! jpegenc quality=85 ! appsink name=sink sync=false max-buffers=2 drop=false')
    pipeline.get_by_name('input').set_property('location',str(video));sink=pipeline.get_by_name('sink')
    pipeline.set_state(Gst.State.PLAYING)
    try:
        index=0
        while True:
            sample=sink.emit('try-pull-sample',10*Gst.SECOND)
            if sample is None:
                error=pipeline.get_bus().pop_filtered(Gst.MessageType.ERROR)
                if error:raise RuntimeError(str(error.parse_error()[0]))
                if not sink.get_property('eos'):raise RuntimeError('Video decoder timed out')
                break
            current=index;index+=1
            if current%10:continue
            buffer=sample.get_buffer();segment=sample.get_segment()
            media_time=segment.to_stream_time(Gst.Format.TIME,buffer.pts)/1e9
            ok,mapped=buffer.map(Gst.MapFlags.READ)
            if not ok:raise RuntimeError('Unable to read decoded video frame')
            pixels=bytes(mapped.data);buffer.unmap(mapped)
            result=call(f'/sessions/{identifier}/frames?seq={len(rows)}&media_time={media_time}',pixels,kind='image/jpeg')
            assert result['engine']=='onnxruntime_cpu' and not result['synthetic'] and result['provenance']=='independent_ai_inference'
            rows.append(dict(source_frame_index=current,**result))
            print(f"frame {current}: {len(result['detections'])} people, {result['processing_latency_ms']:.1f} ms",flush=True)
        if not rows:raise RuntimeError('Video contained no analyzable frames')
        history=call(f'/sessions/{identifier}/incidents')
        if history:
            ack=call('/incidents/'+history[0]['id']+'/acknowledge',{'acknowledged':True},'PATCH')
            assert ack['acknowledged']
            assert any(event['id']==ack['id'] and event['acknowledged'] for event in call(f'/sessions/{identifier}/incidents'))
        latencies=[row['processing_latency_ms'] for row in rows]
        report=dict(session_id=identifier,video_name=video.name,video_sha256=hashlib.sha256(video.read_bytes()).hexdigest(),config=config,capability=status,frames=rows,final=call(f'/sessions/{identifier}'),incidents=call(f'/sessions/{identifier}/incidents'),acknowledgment_verified=bool(history),latency_ms=dict(min=min(latencies),median=statistics.median(latencies),max=max(latencies)),scope='CPU JPEG decode/preprocess/ORT/postprocess; not live camera FPS or TensorRT benchmark',physical_camera_hardware_test='NOT TESTED',tracking='experimental IoU associations, not verified identities')
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
        print(f'Wrote {args.output}; {len(rows)} genuinely inferred frames; {len(history)} incidents')
    finally:
        pipeline.set_state(Gst.State.NULL)
        call(f'/sessions/{identifier}/stop',{},'POST')


if __name__=='__main__':main()
