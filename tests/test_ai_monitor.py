"""Business logic/transport tests. Mocked inference is NOT genuine YOLO evidence."""
import asyncio
import json
from pathlib import Path
import threading
from fastapi.testclient import TestClient
import pytest
from backend.ai_monitor import create_ai_app,UnavailableDetector,EstimatedTracker,MAX_FRAME_BYTES

POLYGON=[[.4,.35],[.9,.35],[.9,.9],[.4,.9]]
JPEG=b'\xff\xd8test-fixture-not-a-real-decoded-jpeg\xff\xd9'


class FixtureDetector:
    """Explicit model substitute: only tests surrounding protocol and event logic."""
    def __init__(self):self.calls=0;self.results=[]
    def status(self):return {'available':True,'engine':'MOCK_DETECTOR_NOT_REAL_AI'}
    def detect(self,data):
        self.calls+=1
        return dict(width=1280,height=720,detections=self.results,processing_latency_ms=3.5,processing_fps=1000/3.5,model_sha256='test-only-not-a-real-model-hash',engine='MOCK_DETECTOR_NOT_REAL_AI')


def source(client,kind='simulation'):
    response=client.post('/api/ai/sessions',json=dict(name='Isolated test',source_type=kind,polygon=POLYGON))
    assert response.status_code==201,response.text
    return response.json()['id']


def test_complete_simulation_entries_hold_exit_reentry_no_duplicates_and_ws(tmp_path):
    with TestClient(create_ai_app(tmp_path/'ai-only',UnavailableDetector())) as client:
        identifier=source(client)
        with client.websocket_connect('/ws/ai/'+identifier) as ws:
            assert ws.receive_json()['type']=='status'
            frames=[]
            for step in range(9):
                response=client.post(f'/api/ai/sessions/{identifier}/simulation/step',json={'seq':step})
                assert response.status_code==200,response.text
                result=response.json();frames.append(result)
                assert result['provenance']=='SIMULATED_TEST_DATA' and result['synthetic']
                message=ws.receive_json();assert message['type']=='frame'
                assert message['payload']['seq']==step
                for _ in result['incidents']:assert ws.receive_json()['type']=='incident'
                assert ws.receive_json()['type']=='status'
            # HTTP retry does not rerun the engine or append another incident.
            repeated=client.post(f'/api/ai/sessions/{identifier}/simulation/step',json={'seq':8}).json()
            assert repeated['seq']==8
            assert client.post(f'/api/ai/sessions/{identifier}/simulation/step').status_code==409
        assert [f['transitions']['entries'] for f in frames]==[0,0,1,0,0,0,1,0,0]
        assert sum(f['transitions']['exits'] for f in frames)==2
        assert sum(f['transitions']['reentries'] for f in frames)==1
        events=client.get(f'/api/ai/sessions/{identifier}/incidents').json()
        assert len(events)==2 and all(event['synthetic'] and event['session_id']==identifier for event in events)
        assert client.get(f'/api/ai/sessions/{identifier}').json()['active_intrusions']==0


def test_sessions_isolated_and_ack_survives_restart(tmp_path):
    directory=tmp_path/'ai'
    v2=tmp_path/'v2.sqlite3';v2.write_bytes(b'unchanged-v2-sentinel')
    original=v2.read_bytes()
    with TestClient(create_ai_app(directory,UnavailableDetector())) as client:
        first=source(client);second=source(client)
        for _ in range(3):client.post(f'/api/ai/sessions/{first}/simulation/step')
        event=client.get(f'/api/ai/sessions/{first}/incidents').json()[0]
        assert client.get(f'/api/ai/sessions/{second}/incidents').json()==[]
        assert client.patch('/api/ai/incidents/'+event['id']+'/acknowledge',json={'acknowledged':True}).json()['acknowledged']
        assert not client.get('/api/ai/status').json()['inference']['available']
    assert v2.read_bytes()==original
    with TestClient(create_ai_app(directory,UnavailableDetector())) as recovered:
        events=recovered.get(f'/api/ai/sessions/{first}/incidents').json()
        assert len(events)==1 and events[0]['acknowledged']
        assert recovered.get(f'/api/ai/sessions/{first}').json()['state']=='stopped'
        assert recovered.post(f'/api/ai/sessions/{first}/resume').status_code==409
        assert recovered.post(f'/api/ai/sessions/{first}/simulation/step').status_code==409


def test_real_source_cannot_silently_fall_back_to_fixture(tmp_path):
    with TestClient(create_ai_app(tmp_path/'ai',UnavailableDetector('runtime not installed'))) as client:
        identifier=source(client,'virtual_video')
        response=client.post(f'/api/ai/sessions/{identifier}/frames?seq=1&media_time=0',content=JPEG,headers={'content-type':'image/jpeg'})
        assert response.status_code==501
        assert client.post(f'/api/ai/sessions/{identifier}/simulation/step').status_code==409
        assert client.get(f'/api/ai/sessions/{identifier}/incidents').json()==[]
        assert client.get('/api/ai/status').json()['physical_camera_hardware_test']=='NOT TESTED'


def test_frame_protocol_correlates_sequence_time_and_mock_provenance(tmp_path):
    detector=FixtureDetector()
    with TestClient(create_ai_app(tmp_path/'ai',detector)) as client:
        identifier=source(client,'uploaded_video')
        endpoint=f'/api/ai/sessions/{identifier}/frames'
        result=client.post(endpoint+'?seq=1&media_time=0',content=JPEG,headers={'content-type':'image/jpeg'}).json()
        assert result['seq']==1 and result['media_time']==0 and result['detections']==[]
        assert not result['synthetic'] and result['engine']=='MOCK_DETECTOR_NOT_REAL_AI'
        assert result['processing_latency_ms']==3.5
        assert client.post(endpoint+'?seq=1&media_time=0',content=JPEG,headers={'content-type':'image/jpeg'}).status_code==200
        assert detector.calls==1
        assert client.post(endpoint+'?seq=1&media_time=0',content=JPEG+b'changed',headers={'content-type':'image/jpeg'}).status_code==409
        assert client.post(endpoint+'?seq=2&media_time=0',content=JPEG,headers={'content-type':'image/jpeg'}).status_code==409
        assert client.post(endpoint+'?seq=0&media_time=1',content=JPEG,headers={'content-type':'image/jpeg'}).status_code==409
        assert client.post(endpoint+'?seq=2&media_time=nan',content=JPEG,headers={'content-type':'image/jpeg'}).status_code==422


def test_frame_limits_bad_images_and_pause_stop(tmp_path):
    with TestClient(create_ai_app(tmp_path/'ai',FixtureDetector())) as client:
        identifier=source(client,'usb_camera');endpoint=f'/api/ai/sessions/{identifier}/frames?seq=1&media_time=0'
        assert client.post(endpoint,content=b'x',headers={'content-type':'text/plain'}).status_code==415
        assert client.post(endpoint,content=b'not jpeg',headers={'content-type':'image/jpeg'}).status_code==422
        assert client.post(endpoint,content=b'\xff\xd8'+bytes(MAX_FRAME_BYTES),headers={'content-type':'image/jpeg'}).status_code==413
        assert client.post(f'/api/ai/sessions/{identifier}/pause').json()['state']=='paused'
        assert client.post(endpoint,content=JPEG,headers={'content-type':'image/jpeg'}).status_code==409
        assert client.post(f'/api/ai/sessions/{identifier}/resume').json()['state']=='running'
        assert client.post(f'/api/ai/sessions/{identifier}/stop').json()['state']=='stopped'
        assert client.post(f'/api/ai/sessions/{identifier}/resume').status_code==409


def test_zone_validation_source_mix_and_active_session_bound(tmp_path):
    with TestClient(create_ai_app(tmp_path/'ai',UnavailableDetector())) as client:
        bad=dict(name='Bad',source_type='simulation',polygon=[[0,0],[1,1]])
        assert client.post('/api/ai/sessions',json=bad).status_code==422
        first=source(client)
        assert client.post(f'/api/ai/sessions/{first}/frames?seq=1&media_time=0',content=JPEG,headers={'content-type':'image/jpeg'}).status_code==409
        assert client.put(f'/api/ai/sessions/{first}/zone',json={'polygon':POLYGON,'confidence_threshold':.7}).json()['zone']['confidence_threshold']==.7
        for _ in range(7):source(client)
        assert client.post('/api/ai/sessions',json=dict(source_type='simulation',polygon=POLYGON)).status_code==429
        client.post(f'/api/ai/sessions/{first}/stop')
        source(client)


def test_estimated_tracker_multiple_people_short_miss_and_expiry():
    tracker=EstimatedTracker()
    def person(x):return dict(class_name='person',confidence=.9,bbox=[x,.2,x+.1,.8])
    first=tracker.update([person(.1),person(.6)],0)
    tracker.update([],0.2)
    next=tracker.update([person(.11),person(.61)],.4)
    assert [d['track_id'] for d in first]==[d['track_id'] for d in next]
    # CPU inference may sample more slowly than one second per media frame.
    retained=tracker.update([person(.12)],1.5)
    assert retained[0]['track_id']==first[0]['track_id']
    expired=tracker.update([person(.12)],5)
    assert expired[0]['track_id'] not in {d['track_id'] for d in first}


def test_single_worker_backpressure_and_stop_discards_inflight_result(tmp_path):
    entered=threading.Event();release=threading.Event()
    class BlockingFixture(FixtureDetector):
        def detect(self,data):entered.set();release.wait(3);return super().detect(data)
    with TestClient(create_ai_app(tmp_path/'ai',BlockingFixture())) as client:
        first=source(client,'virtual_video');second=source(client,'usb_camera')
        responses=[]
        thread=threading.Thread(target=lambda:responses.append(client.post(f'/api/ai/sessions/{first}/frames?seq=1&media_time=0',content=JPEG,headers={'content-type':'image/jpeg'})))
        thread.start();assert entered.wait(2)
        rejected=client.post(f'/api/ai/sessions/{second}/frames?seq=1&media_time=0',content=JPEG,headers={'content-type':'image/jpeg'})
        assert rejected.status_code==429
        client.post(f'/api/ai/sessions/{first}/stop');release.set();thread.join(3)
        assert responses[0].status_code==409
        assert client.get(f'/api/ai/sessions/{first}/incidents').json()==[]
        assert not client.get('/api/ai/status').json()['worker_busy']


def test_fixture_multiple_people_occlusion_and_observed_exit_without_spam(tmp_path):
    """Known fixture boxes exercise event state; this never calls a real detector."""
    from datetime import datetime,timezone
    from backend.ai_monitor import MonitorSession
    from backend.models import Zone
    session=MonitorSession(tmp_path,dict(id='fixture-source',name='Multiple-person fixture',source_type='simulation',created_at=datetime.now(timezone.utc).isoformat()))
    session.db.save_zone(Zone(id='fixture-zone',name='Restricted',camera_id='fixture-source',polygon=POLYGON).model_dump(mode='json'))
    def person(track,x):return dict(track_id=track,class_name='person',confidence=.95,bbox=[x-.05,.2,x+.05,.8])
    async def run():
        first=await session.process([person('known-one',.6),person('known-two',.7)],1280,720,0,0,'fixture-0')
        assert len(first['incidents'])==2
        missed=await session.process([],1280,720,1,.25,'fixture-1')
        assert not missed['incidents'] and missed['status']['active_intrusions']==0
        returned=await session.process([person('known-one',.6),person('known-two',.7)],1280,720,2,.5,'fixture-2')
        assert not returned['incidents'] and returned['status']['active_intrusions']==2
        exited=await session.process([person('known-one',.2),person('known-two',.2)],1280,720,3,.75,'fixture-3')
        assert exited['transitions']['exits']==2 and len(session.db.incidents())==2
    asyncio.run(run());session.db.conn.close()


def test_lost_track_timeout_is_not_reported_as_observed_exit_and_history_is_bounded(tmp_path):
    from datetime import datetime,timezone
    from backend.ai_monitor import MonitorSession
    from backend.models import Zone
    session=MonitorSession(tmp_path,dict(id='timeout-source',name='Timeout fixture',source_type='simulation',created_at=datetime.now(timezone.utc).isoformat()))
    session.db.save_zone(Zone(id='timeout-zone',name='Restricted',camera_id='timeout-source',polygon=POLYGON).model_dump(mode='json'))
    async def run():
        inside=[dict(track_id='known-fixture',class_name='person',confidence=.95,bbox=[.5,.2,.7,.8])]
        assert len((await session.process(inside,1280,720,0,0,'fixture-in'))['incidents'])==1
        lost=await session.process([],1280,720,1,4,'fixture-lost')
        assert lost['transitions']['exits']==0
        assert not session.engine.states and not session.ever_inside
        # A late reacquisition is a new observation, not a verified reentry.
        returned=await session.process(inside,1280,720,2,4.25,'fixture-reacquired')
        assert returned['transitions']['reentries']==0
    asyncio.run(run());session.db.conn.close()


def test_cancelled_http_frame_keeps_inference_slot_until_thread_finishes(tmp_path):
    from fastapi import HTTPException
    from starlette.requests import Request
    from backend.ai_monitor import SessionInput
    entered=threading.Event();release=threading.Event()
    class SlowFixture(FixtureDetector):
        def detect(self,data):
            entered.set();release.wait(3)
            return super().detect(data)
    app=create_ai_app(tmp_path/'cancel-safe',SlowFixture())
    endpoints={getattr(route,'path',None):getattr(route,'endpoint',None) for route in app.routes}
    async def run():
        created=await endpoints['/api/ai/sessions'](SessionInput(source_type='virtual_video',polygon=POLYGON))
        async def receive():return {'type':'http.request','body':JPEG,'more_body':False}
        request=Request({'type':'http','method':'POST','headers':[(b'content-type',b'image/jpeg')]},receive)
        task=asyncio.create_task(endpoints['/api/ai/sessions/{session_id}/frames'](created['id'],request,seq=1,media_time=0))
        for _ in range(200):
            if entered.is_set():break
            await asyncio.sleep(.01)
        assert entered.is_set()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
        assert app.state.worker.locked()
        assert app.state.sessions[created['id']].inflight
        with pytest.raises(HTTPException) as error:
            await endpoints['/api/ai/sessions/{session_id}/frames'](created['id'],request,seq=2,media_time=1)
        assert error.value.status_code==429
        release.set()
        for _ in range(200):
            if not app.state.worker.locked():break
            await asyncio.sleep(.01)
        assert not app.state.worker.locked()
        assert app.state.sessions[created['id']].db.incidents()==[]
        for session in app.state.sessions.values():session.db.conn.close()
    try:asyncio.run(run())
    finally:release.set()


def test_session_threshold_filters_before_tracker_without_false_exit(tmp_path):
    detector=FixtureDetector()
    def person(confidence):return dict(class_name='person',confidence=confidence,bbox=[.5,.2,.7,.8])
    with TestClient(create_ai_app(tmp_path/'confidence-only',detector)) as client:
        identifier=source(client,'virtual_video')
        endpoint=f'/api/ai/sessions/{identifier}/frames'
        detector.results=[person(.9),dict(class_name='person',confidence=.4,bbox=[.1,.1,.2,.6])]
        first=client.post(endpoint+'?seq=1&media_time=0',content=JPEG,headers={'content-type':'image/jpeg'}).json()
        assert len(first['detections'])==1 and len(first['incidents'])==1
        track=first['detections'][0]['track_id']
        detector.results=[person(.4)]
        uncertain=client.post(endpoint+'?seq=2&media_time=0.25',content=JPEG,headers={'content-type':'image/jpeg'}).json()
        assert uncertain['detections']==[] and uncertain['transitions']['exits']==0
        detector.results=[person(.9)]
        returned=client.post(endpoint+'?seq=3&media_time=0.5',content=JPEG,headers={'content-type':'image/jpeg'}).json()
        assert returned['detections'][0]['track_id']==track and not returned['incidents']
        assert len(client.get(f'/api/ai/sessions/{identifier}/incidents').json())==1


def test_independent_incident_entry_basis_distinguishes_initial_inside_from_observed_crossing(tmp_path):
    from datetime import datetime,timezone
    from backend.ai_monitor import MonitorSession
    from backend.models import Zone
    session=MonitorSession(tmp_path,dict(id='basis-source',name='Entry basis fixture',source_type='simulation',created_at=datetime.now(timezone.utc).isoformat()))
    session.db.save_zone(Zone(id='basis-zone',name='Restricted',camera_id='basis-source',polygon=POLYGON).model_dump(mode='json'))
    def person(track,x):return dict(track_id=track,class_name='person',confidence=.95,bbox=[x-.05,.2,x+.05,.8])
    async def run():
        first=await session.process([person('initially-inside',.6),person('initially-outside',.2)],1280,720,0,0,'basis-0')
        assert len(first['incidents'])==1
        assert first['incidents'][0]['entry_basis']=='first_observed_inside'
        entered=await session.process([person('initially-inside',.6),person('initially-outside',.6)],1280,720,1,.25,'basis-1')
        assert len(entered['incidents'])==1
        assert entered['incidents'][0]['entry_basis']=='observed_outside_to_inside'
        assert {event['entry_basis'] for event in session.db.incidents()}=={'first_observed_inside','observed_outside_to_inside'}
        # Expired state cannot establish a visually observed crossing on reacquisition.
        reacquired=await session.process([person('initially-outside',.6)],1280,720,2,4,'basis-expired')
        assert reacquired['incidents'][0]['entry_basis']=='first_observed_inside'
    asyncio.run(run());session.db.conn.close()
