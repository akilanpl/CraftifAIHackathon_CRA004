"""Artificial minimal fixtures test replay mechanics, not judging evidence."""
import json
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.main import create_app
from backend.replay import load_export


def batch():
    frames=[]
    # First observation outside, entry, disappearance, held entry, exit/reentry.
    for index,left in enumerate([10,60,None,60,10,60]):
        obj=[] if left is None else [dict(id=0,class_id=0,label='person',confidence=.9,bbox=dict(left=left,top=20,width=10,height=50))]
        frames.append(dict(frame=index,source_id=0,pts_ns=100000000+index*100000000,width=100,height=100,objects=obj,analytics=[dict(roi_counts={'restricted_zone':99})]))
    return dict(frames=frames)


def source(tmp_path,data=None):
    path=tmp_path/'genuine-shaped-test.json'
    path.write_text(json.dumps(data or batch()))
    return path


def wait_state(client,state):
    deadline=time.monotonic()+3
    while time.monotonic()<deadline:
        result=client.get('/api/replay').json()
        if result['state']==state:
            return result
        if result['state']=='error':
            pytest.fail(result['error'])
        time.sleep(.005)
    pytest.fail('Replay did not reach '+state)


def test_replay_entry_hold_observed_exit_session_restart(tmp_path):
    app=create_app(tmp_path/'replay.db',mode='replay',replay_path=source(tmp_path))
    with TestClient(app) as client:
        initial=client.get('/api/replay').json()
        assert initial['configured'] and initial['total_frames']==6
        assert initial['person_observations']==5 and initial['unique_track_ids']==1
        assert initial['source_path']=='genuine-shaped-test.json'
        first=client.post('/api/replay/start',json={'speed':32}).json()
        final=wait_state(client,'completed')
        assert final['current_frame_index']==5 and final['pts_ns']==600000000
        events=client.get('/api/incidents').json()
        assert len(events)==2  # count telemetry 99 is not a native event
        assert all(e['source']=='pipegen_replay' and e['synthetic'] is False for e in events)
        assert all(e['timestamp_basis']=='replay_session_clock' for e in events)
        assert all(e['entry_basis']=='observed_outside_to_inside' for e in events)
        assert {e['replay']['pts_ns'] for e in events}=={200000000,600000000}
        assert events[0]['replay']['original_track_ids'][events[0]['track_id']]=='0'
        assert app.state.engine.occupancy==1
        second=client.post('/api/replay/start',json={'speed':32}).json()
        wait_state(client,'completed')
        assert second['session_id']!=first['session_id']
        assert len(client.get('/api/incidents').json())==4
        status=client.get('/api/status').json()
        assert status['mode']=='replay' and status['source']=='pipegen_replay'
        assert status['replay']['completed']
        assert client.post('/api/ingest/pipegen',json={}).status_code==409
        assert client.post('/api/synthetic/step').status_code==409
        canonical={k:v for k,v in app.state.replay.latest.items() if k not in ('source','synthetic')}
        assert client.post('/api/ingest/detections',json=canonical).status_code==409
        assert client.post('/api/replay/stop').json()['state']=='stopped'
        assert app.state.engine.occupancy==0


def test_pause_resume_preserves_progress(tmp_path):
    data=batch()
    for i,f in enumerate(data['frames']):
        f['pts_ns']=i*500000000
    app=create_app(tmp_path/'pause.db',mode='replay',replay_path=source(tmp_path,data))
    with TestClient(app) as client:
        client.post('/api/replay/start',json={'speed':1})
        paused=client.post('/api/replay/pause').json()
        time.sleep(.08)
        assert client.get('/api/replay').json()['current_frame_index']==paused['current_frame_index']
        assert client.post('/api/replay/resume').json()['state']=='running'
        assert client.post('/api/replay/stop').json()['state']=='stopped'
        assert client.post('/api/replay/resume').status_code==409


@pytest.mark.parametrize('change',[
    lambda d:d['frames'][1].update(pts_ns=0),
    lambda d:d['frames'][1]['objects'][0].update(label='car'),
    lambda d:d['frames'][1]['objects'][0].update(confidence=float('nan')),
    lambda d:d['frames'][1]['objects'][0]['bbox'].update(width=100),
    lambda d:d['frames'][1].update(objects=None),
    lambda d:d['frames'][1].update(width=True),
])
def test_invalid_whole_batch_has_no_partial_ingestion(tmp_path,change):
    data=batch();change(data)
    app=create_app(tmp_path/'bad.db',mode='replay',replay_path=source(tmp_path,data))
    with TestClient(app) as client:
        assert not client.get('/api/replay').json()['configured']
        assert client.post('/api/replay/start',json={'speed':32}).status_code==422
        assert client.get('/api/incidents').json()==[]
        assert not app.state.engine.states


def test_sentinel_id_and_other_classes_excluded(tmp_path):
    data=batch();data['frames'][1]['objects'][0]['id']=2**64-1
    data['frames'][3]['objects'][0]['id']=-1
    other=dict(id=2,class_id=2,label='car',confidence=.8,bbox=dict(left=0,top=0,width=10,height=10))
    data['frames'][0]['objects'].append(other)
    frames,observations,tracks=load_export(source(tmp_path,data))
    assert frames[1]['detections'][0]['track_id'] is None
    assert frames[3]['detections'][0]['track_id'] is None
    assert len(frames[0]['detections'])==1 and observations==5 and tracks==1


def test_missing_configuration_wrong_mode_and_speed(tmp_path):
    with TestClient(create_app(tmp_path/'none.db',mode='replay')) as client:
        assert not client.get('/api/replay').json()['configured']
        assert client.post('/api/replay/start',json={}).status_code==422
        assert client.post('/api/replay/start',json={'speed':0}).status_code==422
    with TestClient(create_app(tmp_path/'live.db',mode='live')) as client:
        assert client.get('/api/replay').status_code==409
        assert client.post('/api/replay/start',json={}).status_code==409


def test_websocket_receives_latest_replay_frame(tmp_path):
    app=create_app(tmp_path/'ws.db',mode='replay',replay_path=source(tmp_path))
    with TestClient(app) as client:
        client.post('/api/replay/start',json={'speed':32})
        wait_state(client,'completed')
        with client.websocket_connect('/ws/live') as ws:
            assert ws.receive_json()['type']=='status'
            assert ws.receive_json()['type']=='zones'
            received=ws.receive_json()
            assert received['type']=='frame'
            assert received['payload']['replay']['frame_index']==5


def test_first_seen_inside_is_not_claimed_crossing(tmp_path):
    data=batch()
    data['frames']=data['frames'][1:]
    app=create_app(tmp_path/'initial.db',mode='replay',replay_path=source(tmp_path,data))
    with TestClient(app) as client:
        client.post('/api/replay/start',json={'speed':32})
        wait_state(client,'completed')
        events=client.get('/api/incidents').json()
        first=min(events,key=lambda e:e['replay']['frame_index'])
        assert first['entry_basis']=='first_observed_inside'
        assert events[0]['replay']['raw_roi_counts']==[{'restricted_zone':99}]


def test_invalid_replacement_export_leaves_running_session_unchanged(tmp_path):
    path=source(tmp_path)
    app=create_app(tmp_path/'replace.db',mode='replay',replay_path=path)
    with TestClient(app) as client:
        client.post('/api/replay/start',json={'speed':.1})
        client.post('/api/replay/pause')
        old=client.get('/api/replay').json()
        path.write_text('{"frames": []}')
        assert client.post('/api/replay/start',json={'speed':32}).status_code==422
        current=client.get('/api/replay').json()
        assert current['session_id']==old['session_id'] and current['state']=='paused'
        client.post('/api/replay/stop')


def test_visible_occupancy_excludes_missing_but_preserves_dedup(tmp_path):
    from datetime import datetime,timezone,timedelta
    from backend.models import Frame
    app=create_app(tmp_path/'visible.db',mode='replay',replay_path=source(tmp_path))
    engine=app.state.engine
    stamp=datetime.now(timezone.utc)
    def observed(step,present=True,confidence=.9):
        return Frame(timestamp=stamp+timedelta(seconds=step),camera_id='cam-01',frame_width=100,frame_height=100,
                     detections=[dict(track_id='same-track',class_name='person',confidence=confidence,bbox=[.6,.2,.7,.7])] if present else [])
    assert len(engine.process(observed(0),'pipegen_replay')[0])==1
    assert engine.occupancy==1
    assert not engine.process(observed(60,present=False),'pipegen_replay')[0]
    assert engine.occupancy==0
    assert next(iter(engine.states.values()))['inside'] is True
    assert not engine.process(observed(120),'pipegen_replay')[0]
    assert engine.occupancy==1
    assert not engine.process(observed(121,confidence=.1),'pipegen_replay')[0]
    assert engine.occupancy==0
    assert not engine.process(observed(122),'pipegen_replay')[0]
    assert engine.occupancy==1
    engine.clear_zone('replay-restricted-zone')
    assert engine.occupancy==0
    app.state.db.conn.close()
