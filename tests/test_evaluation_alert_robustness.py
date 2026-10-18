"""Deterministic alert audit: fixtures and direct handlers, never actual inference.

Passing characterization tests can confirm a limitation. The JSON report keeps
those outcomes separate from verified contracts. No V2 database is opened.
"""
import asyncio
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import time
from uuid import uuid4
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from starlette.requests import Request
from backend.ai_monitor import (MonitorSession, SessionInput, EstimatedTracker,
                               UnavailableDetector, create_ai_app, MAX_FRAME_BYTES)
from backend.models import Zone

POLYGON=[[.4,.35],[.9,.35],[.9,.9],[.4,.9]]
JPEG=b'\xff\xd8BUSINESS_LOGIC_FIXTURE_ONLY\xff\xd9'
RESULTS={}


@pytest.fixture(scope='session',autouse=True)
def write_evaluation_report():
    yield
    cases=list(RESULTS.values())
    report=dict(schema_version=1,scope='Deterministic fixture business logic and direct API handler audit',
        real_model_inference_executed=False,physical_camera_hardware_test='NOT TESTED',
        websocket_scope='In-process socket doubles; no browser or network transport claim',
        database_scope='Temporary isolated test databases only; V2 databases never opened',
        pytest_case_count=len(cases),assertion_cases_passed=sum(c['assertions_completed'] for c in cases),
        verified_contract_cases=sum(c['classification']=='VERIFIED_CONTRACT' for c in cases),
        observed_limitation_cases=sum(c['classification']=='OBSERVED_LIMITATION' for c in cases),
        unexpected_failure_cases=sum(not c['assertions_completed'] for c in cases),
        interpretation='Passing tests characterize current behavior; observed limitations are not robustness successes.',
        not_evaluated=['Real detector accuracy','Browser permission handling','Physical USB hardware','V2 full regression','Actual network WebSocket delivery'],
        cases=cases)
    target=Path(__file__).resolve().parents[1]/'evidence/evaluation/alert-robustness-tests.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,indent=2)+'\n')


@pytest.fixture
def record(request):
    entry=dict(case=request.node.name,assertions_completed=False,classification='FAILED_OR_INTERRUPTED',observations={})
    RESULTS[request.node.name]=entry
    def complete(observations,limitation=None):
        entry.update(assertions_completed=True,classification='OBSERVED_LIMITATION' if limitation else 'VERIFIED_CONTRACT',observations=observations)
        if limitation:entry['limitation']=limitation
    return complete


@pytest.fixture
def session(tmp_path):
    value=MonitorSession(tmp_path,dict(id=str(uuid4()),name='SIMULATED TEST DATA evaluation',source_type='simulation',created_at='2026-10-18T00:00:00+00:00'))
    value.db.save_zone(Zone(id='audit-zone',name='Fixture restricted region',camera_id=value.id,polygon=POLYGON).model_dump(mode='json'))
    yield value
    value.db.conn.close()


def person(track='known-fixture-track',x=.6,confidence=.95,y=.8):
    return dict(track_id=track,class_name='person',confidence=confidence,bbox=[x-.05,.2,x+.05,y])


async def frames(session,observations,times=None):
    output=[]
    for index,detections in enumerate(observations):
        output.append(await session.process(detections,1280,720,index,times[index] if times else index*.25,'fixture-'+str(index)))
    return output


class NeverInfer:
    """Capabilities-only test double. Calling detect is a test failure, not AI."""
    def __init__(self):self.calls=0
    def status(self):return dict(available=True,engine='FIXTURE_PROTOCOL_ONLY_NO_INFERENCE')
    def detect(self,data):
        self.calls+=1
        raise AssertionError('This business-logic evaluation must never execute inference')


def endpoints(app):
    return {getattr(route,'path',None):getattr(route,'endpoint',None) for route in app.routes}


def jpeg_request(body=JPEG,mime='image/jpeg'):
    sent=False
    async def receive():
        nonlocal sent
        if sent:return {'type':'http.disconnect'}
        sent=True
        return {'type':'http.request','body':body,'more_body':False}
    return Request({'type':'http','method':'POST','headers':[(b'content-type',mime.encode())]},receive)


def close(app):
    for value in app.state.sessions.values():value.db.conn.close()


def test_case_01_empty_frames_are_safe(session,record):
    result=asyncio.run(frames(session,[[],[],[]]))
    assert not session.db.incidents()
    assert all(r['status']['active_intrusions']==0 and not r['incidents'] for r in result)
    record(dict(frames=3,incidents=0,final_occupancy=0))


def test_case_02_entry_then_long_hold_is_one_alert(session,record):
    result=asyncio.run(frames(session,[[person(x=.2)]]+[[person()]]*10))
    assert len(session.db.incidents())==1
    assert sum(len(r['incidents']) for r in result)==1
    assert result[1]['incidents'][0]['entry_basis']=='observed_outside_to_inside'
    record(dict(frames=11,inside_frames=10,incidents=1,entry_basis='observed_outside_to_inside'))


def test_case_03_initial_inside_is_not_a_claimed_crossing(session,record):
    result=asyncio.run(frames(session,[[person()]]))[0]
    assert result['incidents'][0]['entry_basis']=='first_observed_inside'
    assert result['incidents'][0]['synthetic'] and result['provenance']=='SIMULATED_TEST_DATA'
    record(dict(incidents=1,entry_basis='first_observed_inside',synthetic=True))


def test_case_04_exit_and_reentry_use_observed_positions(session,record):
    result=asyncio.run(frames(session,[[person(x=.2)],[person()],[person()],[person(x=.2)],[person()],[person(x=.2)]]))
    assert len(session.db.incidents())==2
    assert sum(r['transitions']['exits'] for r in result)==2
    assert sum(r['transitions']['reentries'] for r in result)==1
    record(dict(alerts=2,observed_exits=2,observed_reentries=1))


def test_case_05_multiple_people_do_not_share_entry_state(session,record):
    result=asyncio.run(frames(session,[[person('one',.2),person('two',.3)],[person('one',.6),person('two',.7)],[person('one',.6),person('two',.7)]]))
    assert len(session.db.incidents())==2
    assert {event['track_id'] for event in session.db.incidents()}=={'one','two'}
    assert result[-1]['status']['active_intrusions']==2 and not result[-1]['incidents']
    record(dict(distinct_fixture_tracks=2,incidents=2,held_duplicate_alerts=0))


def test_case_06_low_confidence_does_not_make_false_exit(session,record):
    result=asyncio.run(frames(session,[[person(confidence=.4)],[person()],[person(x=.2,confidence=.4)],[person()]]))
    assert not result[0]['incidents']
    assert len(session.db.incidents())==1
    assert sum(r['transitions']['exits'] for r in result)==0
    record(dict(threshold=.5,low_confidence=.4,incidents=1,false_exits=0))


def test_case_07_missing_tracking_id_is_not_invented(session,record):
    result=asyncio.run(frames(session,[[person(track=None)]]))[0]
    assert not result['incidents'] and result['detections'][0]['track_id'] is None
    assert any('without track_id' in warning for warning in result['warnings'])
    record(dict(missing_ids_skipped=1,incidents=0,warning_emitted=True))


def test_case_08_short_occlusion_is_not_an_exit_or_new_entry(session,record):
    result=asyncio.run(frames(session,[[person()],[],[],[person()]]))
    assert len(session.db.incidents())==1
    assert result[1]['status']['active_intrusions']==0
    assert sum(r['transitions']['exits'] for r in result)==0 and not result[-1]['incidents']
    record(dict(missed_observations=2,incidents=1,observed_exits=0,duplicate_on_return=False))


def test_case_09_long_loss_reacquisition_has_limited_identity_evidence(session,record):
    result=asyncio.run(frames(session,[[person()],[],[person()]],times=[0,4,4.25]))
    assert len(session.db.incidents())==2
    assert result[1]['transitions']['exits']==0 and result[2]['transitions']['reentries']==0
    assert result[2]['incidents'][0]['entry_basis']=='first_observed_inside'
    record(dict(gap_seconds=4,incidents=2,claimed_observed_exits=0,claimed_verified_reentries=0),
           'After the retention timeout, reacquisition can create another initial-inside alert; physical identity is not established.')


def test_case_10_boundary_jitter_can_repeat_alerts_without_hysteresis(session,record):
    result=asyncio.run(frames(session,[[person(x=x)] for x in [.399,.401,.399,.401,.399,.401]]))
    assert len(session.db.incidents())==3
    assert sum(r['transitions']['reentries'] for r in result)==2
    record(dict(boundary_x=.4,jitter_amplitude=.001,observations=6,incidents=3),
           'Default one-frame entry logic has no spatial hysteresis; small boundary jitter produces repeated geometric entries.')


def test_case_11_estimated_id_changes_can_repeat_initial_inside_alerts(session,record):
    tracker=EstimatedTracker()
    first=tracker.update([{k:v for k,v in person(x=.5).items() if k!='track_id'}],0)
    moved=tracker.update([{k:v for k,v in person(x=.8).items() if k!='track_id'}],.25)
    assert first[0]['track_id']!=moved[0]['track_id']
    result=asyncio.run(frames(session,[first,moved]))
    assert len(session.db.incidents())==2
    assert all(r['incidents'][0]['entry_basis']=='first_observed_inside' for r in result)
    record(dict(nonoverlapping_positions=2,estimated_ids=2,incidents=2),
           'Greedy IoU associations cannot prove that a rapidly moving or reassigned track is the same physical person; duplicate physical-person alerts remain possible.')


def test_case_12_polygon_boundary_and_resolution_are_consistent(session,record):
    result=asyncio.run(frames(session,[[person(x=.4)]]))[0]
    assert len(result['incidents'])==1
    assert result['frame_width']==1280 and result['frame_height']==720
    box=result['detections'][0]['bbox']
    assert (box[0]+box[2])/2==.4
    assert session.db.zones()[0]['polygon']==POLYGON
    record(dict(boundary_is_inside=True,frame_dimensions=[1280,720],coordinates='normalized xyxy',browser_alignment_tested=False))


def test_case_13_nonmonotonic_or_nonfinite_media_clock_rejected(tmp_path,record):
    detector=NeverInfer();app=create_ai_app(tmp_path/'clock',detector);api=endpoints(app)
    async def run():
        created=await api['/api/ai/sessions'](SessionInput(source_type='virtual_video',polygon=POLYGON))
        value=app.state.sessions[created['id']];value.last_seq=5;value.last_media_time=2
        checked=[]
        for seq,media,code in [(4,3,409),(6,2,409),(6,1,409),(5,3,409),(6,float('nan'),422),(6,float('inf'),422),(-1,3,422)]:
            with pytest.raises(HTTPException) as caught:
                await api['/api/ai/sessions/{session_id}/frames'](created['id'],jpeg_request(),seq,media)
            assert caught.value.status_code==code;checked.append(code)
        assert detector.calls==0 and not value.db.incidents()
        return checked
    try:codes=asyncio.run(run())
    finally:close(app)
    record(dict(rejected_inputs=7,status_codes=codes,inference_calls=0,incidents=0))


def test_case_14_identical_retry_cached_changed_bytes_rejected(tmp_path,record):
    detector=NeverInfer();app=create_ai_app(tmp_path/'retry',detector);api=endpoints(app)
    async def run():
        created=await api['/api/ai/sessions'](SessionInput(source_type='uploaded_video',polygon=POLYGON))
        value=app.state.sessions[created['id']]
        value.last_seq=1;value.last_media_time=.25;value.last_digest=hashlib.sha256(JPEG).hexdigest()
        value.last_result={'fixture_cached_response':True,'seq':1,'media_time':.25}
        result=await api['/api/ai/sessions/{session_id}/frames'](created['id'],jpeg_request(),1,.25)
        assert result==value.last_result
        with pytest.raises(HTTPException) as caught:
            await api['/api/ai/sessions/{session_id}/frames'](created['id'],jpeg_request(JPEG+b'different'),1,.25)
        assert caught.value.status_code==409 and detector.calls==0
    try:asyncio.run(run())
    finally:close(app)
    record(dict(identical_retry='cached',changed_bytes='409 rejected',inference_calls=0))


def test_case_15_source_and_capture_mismatch_cannot_claim_hardware(record):
    combinations=[('simulation','physical_camera'),('virtual_video','physical_camera'),('uploaded_video','simulated_usb_camera'),('usb_camera','recorded_video')]
    for source,origin in combinations:
        with pytest.raises(ValidationError):SessionInput(source_type=source,capture_origin=origin,polygon=POLYGON)
    record(dict(rejected_origin_source_combinations=len(combinations),hardware_claims_generated=0))


def test_case_16_malformed_shapes_and_oversize_frames_leave_no_incidents(tmp_path,record):
    detector=NeverInfer();app=create_ai_app(tmp_path/'limits',detector);api=endpoints(app)
    async def run():
        for polygon in [[[0,0],[1,1]],[[0,0],[1,1],[0,1],[1,0]],[[0,0],[2,0],[1,1]]]:
            with pytest.raises(HTTPException) as caught:
                await api['/api/ai/sessions'](SessionInput(source_type='virtual_video',polygon=polygon))
            assert caught.value.status_code==422
        created=await api['/api/ai/sessions'](SessionInput(source_type='virtual_video',polygon=POLYGON))
        for body,mime,expected in [(b'', 'image/jpeg',422),(b'not jpeg','image/jpeg',422),(JPEG,'application/json',415),(b'\xff\xd8'+bytes(MAX_FRAME_BYTES),'image/jpeg',413)]:
            with pytest.raises(HTTPException) as caught:
                await api['/api/ai/sessions/{session_id}/frames'](created['id'],jpeg_request(body,mime),1,0)
            assert caught.value.status_code==expected
            assert not app.state.worker.locked()
        assert detector.calls==0 and not app.state.sessions[created['id']].db.incidents()
    try:asyncio.run(run())
    finally:close(app)
    record(dict(invalid_polygons=3,rejected_frame_inputs=4,inference_calls=0,worker_released=True,incidents=0))


def test_case_17_pause_stop_and_worker_backpressure_are_bounded(tmp_path,record):
    detector=NeverInfer();app=create_ai_app(tmp_path/'control',detector);api=endpoints(app)
    async def run():
        created=await api['/api/ai/sessions'](SessionInput(source_type='virtual_video',polygon=POLYGON))
        identifier=created['id'];value=app.state.sessions[identifier]
        await app.state.worker.acquire()
        with pytest.raises(HTTPException) as caught:
            await api['/api/ai/sessions/{session_id}/frames'](identifier,jpeg_request(),1,0)
        assert caught.value.status_code==429;app.state.worker.release()
        await api['/api/ai/sessions/{session_id}/{action}'](identifier,'pause')
        generation=value.generation
        await api['/api/ai/sessions/{session_id}/{action}'](identifier,'pause')
        assert value.generation==generation
        with pytest.raises(HTTPException) as caught:
            await api['/api/ai/sessions/{session_id}/frames'](identifier,jpeg_request(),1,0)
        assert caught.value.status_code==409
        await api['/api/ai/sessions/{session_id}/{action}'](identifier,'resume')
        await api['/api/ai/sessions/{session_id}/{action}'](identifier,'stop')
        with pytest.raises(HTTPException) as caught:await api['/api/ai/sessions/{session_id}/{action}'](identifier,'resume')
        assert caught.value.status_code==409 and value.last_result is None and not value.tracker.tracks
    try:asyncio.run(run())
    finally:close(app)
    record(dict(queue_capacity=0,busy_status=429,paused_and_stopped_status=409,controls_idempotent=True,stale_result_cleared=True))


def test_case_18_session_isolation_restart_and_ack_preserve_history(tmp_path,record):
    root=tmp_path/'independent-only';app=create_ai_app(root,UnavailableDetector());api=endpoints(app)
    async def run():
        first=await api['/api/ai/sessions'](SessionInput(source_type='simulation',polygon=POLYGON))
        second=await api['/api/ai/sessions'](SessionInput(source_type='simulation',polygon=POLYGON))
        one,two=app.state.sessions[first['id']],app.state.sessions[second['id']]
        result=await frames(one,[[person()]])
        event=result[0]['incidents'][0]
        from backend.models import Acknowledge
        await api['/api/ai/incidents/{incident_id}/acknowledge'](event['id'],Acknowledge(acknowledged=True))
        assert not two.db.incidents()
        assert one.directory!=two.directory
        return first['id'],event['id']
    try:identifier,event_id=asyncio.run(run())
    finally:close(app)
    recovered=create_ai_app(root,UnavailableDetector())
    try:
        value=recovered.state.sessions[identifier]
        events=value.db.incidents()
        assert len(events)==1 and events[0]['id']==event_id and events[0]['acknowledged']
        assert value.state=='stopped' and value.engine.occupancy==0
        assert value.transition_counts['entries']==1
    finally:close(recovered)
    record(dict(sessions=2,source_databases_separate=True,recovered_incidents=1,acknowledgment_persisted=True,restart_state='stopped',v2_database_opened=False))


def test_case_19_slow_or_disconnected_socket_does_not_lose_alert(session,record):
    class Healthy:
        def __init__(self):self.messages=[]
        async def send_json(self,value):self.messages.append(value)
    class Slow:
        async def send_json(self,value):await asyncio.sleep(60)
    class Disconnected:
        async def send_json(self,value):raise ConnectionError('Fixture disconnect')
    healthy,slow,disconnected=Healthy(),Slow(),Disconnected()
    session.clients.update([healthy,slow,disconnected])
    started=time.monotonic()
    result=asyncio.run(frames(session,[[person()]]))[0]
    elapsed=time.monotonic()-started
    assert len(session.db.incidents())==1 and len(result['incidents'])==1
    assert slow not in session.clients and disconnected not in session.clients
    assert [message['type'] for message in healthy.messages]==['frame','incident','status']
    assert elapsed>=.9 and elapsed<3
    record(dict(slow_client_removed=True,disconnected_client_removed=True,healthy_message_types=['frame','incident','status'],persisted_incidents=1,measured_handler_seconds=round(elapsed,3)),
           'Broadcast waits up to one second per failing client and sends sequentially; many slow clients can delay the response and hold the single inference slot. This is a transport double, not real network evidence.')


def test_case_20_simulated_usb_is_not_fixture_inference_or_hardware_proof(tmp_path,record):
    app=create_ai_app(tmp_path/'simulated-usb',UnavailableDetector('Deliberately unavailable evaluation worker'));api=endpoints(app)
    async def run():
        created=await api['/api/ai/sessions'](SessionInput(source_type='usb_camera',capture_origin='simulated_usb_camera',polygon=POLYGON))
        assert created['input_is_simulated'] and not created['synthetic']
        assert created['physical_camera_hardware_test']=='NOT TESTED'
        assert created['capture_origin_verified'] is False
        with pytest.raises(HTTPException) as caught:
            await api['/api/ai/sessions/{session_id}/frames'](created['id'],jpeg_request(),1,0)
        assert caught.value.status_code==501
        assert not app.state.sessions[created['id']].db.incidents()
        return created
    try:created=asyncio.run(run())
    finally:close(app)
    record(dict(capture_origin=created['capture_origin'],capture_origin_verified=False,hardware_test='NOT TESTED',unavailable_inference_status=501,fake_fallback_detections=0))
