from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from backend.main import create_app
from backend.geometry import point_in_polygon

POLYGON = [[.4,.3],[.9,.3],[.9,.9],[.4,.9]]

@pytest.fixture
def api(tmp_path):
    app = create_app(tmp_path/'test.sqlite3')
    with TestClient(app) as client:
        zone = client.post('/api/zones',json=dict(name='Hazard',polygon=POLYGON)).json()
        yield client,app,zone


def frame(step=0,x=.6,track='17',confidence=.94,**kwargs):
    return dict(timestamp=(datetime(2026,10,18,tzinfo=timezone.utc)+timedelta(seconds=step)).isoformat(),camera_id='cam-01',frame_width=1280,frame_height=720,detections=[dict(track_id=track,class_name='person',confidence=confidence,bbox=[x-.05,.1,x+.05,.8])],**kwargs)


def test_geometry():
    assert point_in_polygon((.5,.5),POLYGON)
    assert point_in_polygon((.4,.3),POLYGON)
    assert not point_in_polygon((.1,.5),POLYGON)


def test_entry_hold_exit_reentry(api):
    client,app,zone = api
    assert not client.post('/api/ingest/detections',json=frame(x=.2)).json()['incidents']
    first = client.post('/api/ingest/detections',json=frame(1)).json()['incidents']
    assert len(first)==1 and first[0]['source']=='canonical' and not first[0]['synthetic']
    assert not client.post('/api/ingest/detections',json=frame(2)).json()['incidents']
    assert app.state.engine.occupancy==1
    client.post('/api/ingest/detections',json=frame(3,x=.2))
    assert app.state.engine.occupancy==0
    assert len(client.post('/api/ingest/detections',json=frame(4)).json()['incidents'])==1
    assert len(client.get('/api/incidents').json())==2


def test_multiple_tracks_cameras(api):
    client,app,zone=api
    payload=frame()
    payload['detections'].append(dict(track_id='18',class_name='person',confidence=.9,bbox=[.5,.2,.7,.7]))
    assert len(client.post('/api/ingest/detections',json=payload).json()['incidents'])==2
    payload=frame(1)
    payload['camera_id']='other-camera'
    assert not client.post('/api/ingest/detections',json=payload).json()['incidents']


def test_missing_id_low_confidence_other_class(api):
    client,app,zone=api
    result=client.post('/api/ingest/detections',json=frame(track=None)).json()
    assert not result['incidents'] and 'without track_id' in result['warnings'][0]
    assert not client.post('/api/ingest/detections',json=frame(1,confidence=.1)).json()['incidents']
    payload=frame(2)
    payload['detections'][0]['class_name']='forklift'
    assert not client.post('/api/ingest/detections',json=payload).json()['incidents']


@pytest.mark.parametrize('polygon',[[[0,0],[1,1]],[[0,0],[1,1],[0,1],[1,0]],[[0,0],[2,0],[1,1]],[[0,0],[.5,.5],[1,1]],[[0,0],[1,0],[1,1],[0,0]]])
def test_invalid_zone(api,polygon):
    client,_,_=api
    assert client.post('/api/zones',json=dict(name='Bad',polygon=polygon)).status_code==422


def test_invalid_payloads(api):
    client,_,_=api
    assert client.post('/api/ingest/detections',json={}).status_code==422
    bad=frame();bad['detections'][0]['bbox']=[.8,.1,.2,.9]
    assert client.post('/api/ingest/detections',json=bad).status_code==422
    bad=frame();bad['timestamp']='2026-10-18T12:00:00'
    assert client.post('/api/ingest/detections',json=bad).status_code==422
    bad=frame();bad['detections'][0]['bbox']=[0,0,2,1]
    assert client.post('/api/ingest/detections',json=bad).status_code==422


def test_health_status_ack_and_analytics(api):
    client,app,zone=api
    assert client.get('/api/health').json()['status']=='ok'
    assert client.get('/api/status').json()['fps'] is None
    event=client.post('/api/ingest/detections',json=frame()).json()['incidents'][0]
    assert client.get('/api/incidents/'+event['id']).json()['id']==event['id']
    assert client.patch('/api/incidents/'+event['id']+'/acknowledge',json={'acknowledged':True}).json()['acknowledged']
    assert not client.patch('/api/incidents/'+event['id']+'/acknowledge',json={'acknowledged':False}).json()['acknowledged']
    summary=client.get('/api/analytics/summary').json()
    assert summary['total_incidents']==1 and summary['by_severity']=={'high':1}
    assert client.post('/api/ingest/pipegen',json={}).status_code==501
    assert client.post('/api/synthetic/step').status_code==409
    assert client.get('/api/incidents/missing').status_code==404


def test_native_duplicate_and_detection_suppression(api):
    client,app,zone=api
    payload=frame(analytics_mode='native',native_events=[dict(event_id='native-123',zone_id=zone['id'],track_id='17',event_type='zone_entry')])
    assert len(client.post('/api/ingest/detections',json=payload).json()['incidents'])==1
    payload['timestamp']=frame(1)['timestamp']
    assert not client.post('/api/ingest/detections',json=payload).json()['incidents']
    assert len(client.get('/api/incidents').json())==1
    invalid=frame(2,native_events=payload['native_events'])
    assert client.post('/api/ingest/detections',json=invalid).status_code==422


def test_unknown_native_zone_rejected_atomically(api):
    client,app,zone=api
    payload=frame(analytics_mode='native',native_events=[dict(event_id='bad',zone_id='unknown',event_type='zone_entry')])
    assert client.post('/api/ingest/detections',json=payload).status_code==422
    assert not client.get('/api/incidents').json()


def test_persistence_and_native_dedup_restart(tmp_path):
    path=tmp_path/'persist.sqlite3'
    app=create_app(path)
    with TestClient(app) as client:
        zone=client.post('/api/zones',json=dict(name='Hazard',polygon=POLYGON)).json()
        payload=frame(analytics_mode='native',native_events=[dict(event_id='persistent',zone_id=zone['id'],event_type='zone_entry')])
        client.post('/api/ingest/detections',json=payload)
    with TestClient(create_app(path)) as client:
        assert len(client.get('/api/incidents').json())==1
        payload['timestamp']=frame(2)['timestamp']
        assert not client.post('/api/ingest/detections',json=payload).json()['incidents']


def test_stale_and_source_disconnect(tmp_path):
    now=[0]
    app=create_app(tmp_path/'clock.sqlite3',clock=lambda:now[0])
    with TestClient(app) as client:
        client.post('/api/zones',json=dict(name='Hazard',polygon=POLYGON))
        client.post('/api/ingest/detections',json=frame())
        now[0]=6
        assert client.get('/api/status').json()['active_intrusions']==0
        assert len(client.post('/api/ingest/detections',json=frame(1)).json()['incidents'])==1
        now[0]=17
        assert not client.get('/api/status').json()['connected']


def test_debounce_low_confidence_no_false_reentry(api):
    client,app,zone=api
    client.put('/api/zones/'+zone['id'],json=dict(name='Hazard',polygon=POLYGON,debounce_frames=2))
    assert not client.post('/api/ingest/detections',json=frame()).json()['incidents']
    assert len(client.post('/api/ingest/detections',json=frame(1)).json()['incidents'])==1
    client.post('/api/ingest/detections',json=frame(2,confidence=.1))
    assert not client.post('/api/ingest/detections',json=frame(3)).json()['incidents']


def test_zone_crud(api):
    client,app,zone=api
    assert client.put('/api/zones/'+zone['id'],json=dict(name='Updated',polygon=POLYGON)).json()['name']=='Updated'
    assert client.delete('/api/zones/'+zone['id']).status_code==204
    assert client.get('/api/zones').json()==[]
    assert client.delete('/api/zones/'+zone['id']).status_code==404


def test_synthetic_isolation_and_websocket(tmp_path):
    with TestClient(create_app(tmp_path/'synthetic.sqlite3',mode='synthetic')) as client:
        with client.websocket_connect('/ws/live') as socket:
            assert socket.receive_json()['payload']['mode']=='synthetic'
            assert socket.receive_json()['type']=='zones'
            client.post('/api/synthetic/step')
            assert socket.receive_json()['type']=='frame'
            socket.receive_json()
            event=client.post('/api/synthetic/step').json()['incidents'][0]
            assert event['synthetic'] and event['source']=='synthetic'
        assert client.post('/api/ingest/pipegen',json={}).status_code==409
    with TestClient(create_app(tmp_path/'live.sqlite3')) as client:
        assert not client.get('/api/incidents').json()
        assert not client.get('/api/zones').json()


def test_replayed_frame_and_duplicate_track(api):
    client,app,zone=api
    payload=frame()
    client.post('/api/ingest/detections',json=payload)
    assert not client.post('/api/ingest/detections',json=payload).json()['incidents']
    payload=frame(1);payload['detections']*=2
    assert client.post('/api/ingest/detections',json=payload).status_code==422


def test_mixed_native_and_geometry_track_no_double_count(api):
    client,app,zone=api
    assert len(client.post('/api/ingest/detections',json=frame()).json()['incidents'])==1
    payload=frame(1,analytics_mode='native',native_events=[dict(event_id='native-enter',zone_id=zone['id'],track_id='17',event_type='zone_entry')])
    assert not client.post('/api/ingest/detections',json=payload).json()['incidents']
    payload=frame(2,analytics_mode='native',native_events=[dict(event_id='native-exit',zone_id=zone['id'],track_id='17',event_type='zone_exit')])
    assert not client.post('/api/ingest/detections',json=payload).json()['incidents']
    payload=frame(3,analytics_mode='native',native_events=[dict(event_id='native-reenter',zone_id=zone['id'],track_id='17',event_type='zone_entry')])
    assert len(client.post('/api/ingest/detections',json=payload).json()['incidents'])==1
    assert not client.post('/api/ingest/detections',json=frame(4)).json()['incidents']


def test_timezone_normalized_to_utc(api):
    client,app,zone=api
    payload=frame()
    payload['timestamp']='2026-10-18T12:00:00+05:30'
    response=client.post('/api/ingest/detections',json=payload).json()
    assert response['incidents'][0]['timestamp']=='2026-10-18T06:30:00+00:00'
    assert client.get('/api/analytics/summary').json()['trend']==[{'date':'2026-10-18','count':1}]


def test_configured_pipegen_parser_provenance(api):
    client,app,zone=api
    app.state.adapter.parser=lambda raw: frame()
    response=client.post('/api/ingest/pipegen',json={'actual_schema_placeholder':'parser fixture only'})
    assert response.status_code==200
    incident=response.json()['incidents'][0]
    assert incident['source']=='pipegen' and incident['synthetic'] is False
    assert client.get('/api/status').json()['integration_status']=='receiving metadata'


def test_adjacent_polygon_overlap_rejected(api):
    client,_,_=api
    polygon=[[0,0],[1,0],[.5,0],[1,1],[0,1]]
    assert client.post('/api/zones',json=dict(name='Overlapping edge',polygon=polygon)).status_code==422
