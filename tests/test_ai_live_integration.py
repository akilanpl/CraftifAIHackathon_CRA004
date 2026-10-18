"""Opt-in real HTTP/WS checks; requires the independent CPU worker and local real JPEGs.
These are actual model calls, not detection mocks. No physical camera is exercised.
"""
import json
import os
from pathlib import Path
import urllib.request
import urllib.error
import pytest

API=os.getenv('SENTINEL_AI_E2E_URL','')
FRAMES=os.getenv('SENTINEL_AI_E2E_FRAMES','')
pytestmark=pytest.mark.skipif(not API or not FRAMES,reason='Opt-in genuine local CPU worker/frame integration')


def call(path,data=None,method=None,content_type='application/json'):
    raw=data if isinstance(data,bytes) else json.dumps(data).encode() if data is not None else None
    with urllib.request.urlopen(urllib.request.Request(API+path,data=raw,method=method,headers={'Content-Type':content_type}),timeout=20) as response:return json.load(response)


@pytest.mark.parametrize('source_type,capture_origin',[
    ('virtual_video','recorded_video'),
    ('uploaded_video','recorded_video'),
    ('usb_camera','simulated_usb_camera'),
])
def test_genuine_real_pixels_over_http_websocket_and_sqlite(source_type,capture_origin):
    from websockets.sync.client import connect
    capability=call('/status')
    assert capability['inference']['available'] and capability['inference']['providers']==['CPUExecutionProvider']
    session=call('/sessions',dict(source_type=source_type,capture_origin=capture_origin,name='Genuine opt-in HTTP WS acceptance',polygon=[[.55,.45],[.95,.45],[.95,.95],[.55,.95]],confidence_threshold=.5))
    identifier=session['id']
    assert session['capture_origin']==capture_origin
    ws_url=API.replace('http://','ws://').replace('https://','wss://').removesuffix('/api/ai')+'/ws/ai/'+identifier
    try:
        with connect(ws_url,open_timeout=5) as socket:
            assert json.loads(socket.recv(timeout=5))['type']=='status'
            for seq,(index,media_time) in enumerate([(0,0.),(38,1.52)]):
                pixels=(Path(FRAMES)/f'frame-{index:03}.jpg').read_bytes()
                frame=call(f'/sessions/{identifier}/frames?seq={seq}&media_time={media_time}',pixels,content_type='image/jpeg')
                assert frame['session_id']==identifier and frame['seq']==seq and frame['media_time']==media_time
                assert frame['frame_width']==960 and frame['frame_height']==540
                assert frame['engine']=='onnxruntime_cpu' and not frame['synthetic']
                assert frame['capture_origin']==capture_origin and frame['physical_camera_hardware_test']=='NOT TESTED'
                assert len(frame['detections'])==3, 'Reviewed fixture frame contains three visible people'
                assert frame['processing_latency_ms']>0 and frame['processing_fps']>0
                assert all(d['class_name']=='person' and .5<=d['confidence']<=1 for d in frame['detections'])
                event=json.loads(socket.recv(timeout=5));assert event['type']=='frame' and event['payload']['seq']==seq
                for incident in frame['incidents']:
                    event=json.loads(socket.recv(timeout=5));assert event['type']=='incident' and event['payload']['id']==incident['id']
                assert json.loads(socket.recv(timeout=5))['type']=='status'
                retried=call(f'/sessions/{identifier}/frames?seq={seq}&media_time={media_time}',pixels,content_type='image/jpeg')
                assert retried==frame  # identical retry never re-infers or persists a duplicate
            incidents=call(f'/sessions/{identifier}/incidents')
            assert len(incidents)==1 and incidents[0]['entry_basis']=='first_observed_inside'
            incident=incidents[0]
            assert incident['capture_origin']==capture_origin and not incident['synthetic']
            call('/incidents/'+incident['id']+'/acknowledge',{'acknowledged':True},'PATCH')
            assert call(f'/sessions/{identifier}/incidents')[0]['acknowledged']
            assert json.loads(socket.recv(timeout=5))['type']=='incident'
        # A fresh socket recovers the latest authoritative frame and persisted history.
        with connect(ws_url,open_timeout=5) as reconnected:
            assert json.loads(reconnected.recv(timeout=5))['type']=='status'
            assert json.loads(reconnected.recv(timeout=5))['payload']['seq']==1
        call(f'/sessions/{identifier}/pause',{},'POST')
        with pytest.raises(urllib.error.HTTPError) as rejected:
            call(f'/sessions/{identifier}/frames?seq=2&media_time=2.64',(Path(FRAMES)/'frame-066.jpg').read_bytes(),content_type='image/jpeg')
        assert rejected.value.code==409
        call(f'/sessions/{identifier}/resume',{},'POST')
        with pytest.raises(urllib.error.HTTPError) as rejected:
            call(f'/sessions/{identifier}/frames?seq=2&media_time=0',(Path(FRAMES)/'frame-000.jpg').read_bytes(),content_type='image/jpeg')
        assert rejected.value.code==409
        assert len(call(f'/sessions/{identifier}/incidents'))==1
    finally:
        stopped=call(f'/sessions/{identifier}/stop',{},'POST')
        assert stopped['state']=='stopped'
        assert not call('/status')['worker_busy']
