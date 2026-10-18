"""CPU checks of the immutable genuine factory export; no model/inference rerun.

Set SENTINEL_FACTORY_TEST_METADATA to an explicit snapshot override. Source-
independent CI skips these tests only if the preserved artifact is absent.
"""
from datetime import datetime,timezone,timedelta
import hashlib
import json
import os
from pathlib import Path
import pytest
from backend.database import Database
from backend.engine import ZoneEngine
from backend.models import Frame
from backend.replay import load_export

ROOT=Path(__file__).resolve().parents[1]
EXPECTED_SHA='b88db711a3daf13d494c8c438ad8f13b6f5aa262d9d7402e621be83439c9ccce'
POLYGON=[[806/1920,799/1080],[1190/1920,799/1080],[1190/1920,929/1080],[806/1920,929/1080]]


@pytest.fixture
def actual_metadata():
    path=Path(os.getenv('SENTINEL_FACTORY_TEST_METADATA',str(ROOT/'evidence/06-real-metadata/warehouse-fp16-v2-metadata.json')))
    if not path.is_file():pytest.skip('Genuine immutable factory export is not available on this host')
    before=path.read_bytes()
    assert hashlib.sha256(before).hexdigest()==EXPECTED_SHA,'This integration fixture is pinned to the audited factory run; audit a new snapshot before replacing it'
    yield path,json.loads(before)
    assert path.read_bytes()==before,'The genuine source must remain byte-for-byte unchanged'


def test_genuine_factory_export_dimensions_tracks_pts_and_native_roi(actual_metadata):
    path,raw=actual_metadata
    parsed,observations,tracks=load_export(path)
    assert len(parsed)==254 and observations==522 and tracks==6
    assert parsed[0]['pts_ns']==80000000 and parsed[-1]['pts_ns']==10200000000
    assert {b['pts_ns']-a['pts_ns'] for a,b in zip(parsed,parsed[1:])}=={40000000}
    assert {(f['width'],f['height'],f['source_id']) for f in parsed}=={(1920,1080,0)}
    assert {key for f in parsed for analytics in f['raw_roi_counts'] for key in analytics}=={'RestrictedZone'}
    assert min(o['confidence'] for f in raw['frames'] for o in f['objects'])==.5


def test_actual_factory_engine_transitions_no_frame_replay_duplicates_and_ack_recovery(actual_metadata,tmp_path):
    path,raw=actual_metadata
    frames,_,_=load_export(path)
    now=[0.]
    db_path=tmp_path/'factory-only.sqlite3'
    db=Database(db_path)
    db.save_zone(dict(id='factory-audit',name='RestrictedZone',camera_id='factory-01',polygon=POLYGON,severity='high',confidence_threshold=.5,debounce_frames=1))
    engine=ZoneEngine(db,stale_seconds=float('inf'),clock=lambda:now[0],visible_only=True)
    origin=datetime(2000,1,1,tzinfo=timezone.utc)  # Explicit test-only replay-session clock, never capture time.
    inputs=[];events=[]
    for source in frames:
        now[0]=source['pts_ns']/1e9
        frame=Frame(timestamp=origin+timedelta(microseconds=(source['pts_ns']-frames[0]['pts_ns'])//1000),timestamp_basis='replay_session_clock',camera_id='factory-01',frame_width=source['width'],frame_height=source['height'],detections=source['detections'],replay=dict(session_id='factory-audit-test',frame_index=source['frame_index'],pts_ns=source['pts_ns'],source_id=source['source_id'],original_track_ids={d['track_id']:d['track_id'] for d in source['detections'] if d['track_id'] is not None},raw_roi_counts=source['raw_roi_counts']))
        inputs.append(frame)
        produced,_=engine.process(frame,'pipegen_replay')
        events.extend(produced)
    assert len(events)==2
    assert [event['track_id'] for event in events]==['0','0']
    assert all(event['entry_basis']=='observed_outside_to_inside' and not event['synthetic'] and event['source']=='pipegen_replay' for event in events)
    assert [event['timestamp'] for event in events]==[(origin+timedelta(seconds=1.52)).isoformat(),(origin+timedelta(seconds=2.64)).isoformat()]
    assert engine.occupancy==0
    for frame in inputs:
        assert not engine.process(frame,'pipegen_replay')[0]
    assert len(db.incidents())==2
    acknowledged=dict(events[0],acknowledged=True)
    db.save_incident(acknowledged);db.conn.close()
    recovered=Database(db_path)
    assert len(recovered.incidents())==2
    assert next(event for event in recovered.incidents() if event['id']==acknowledged['id'])['acknowledged']
    recovered.conn.close()


def test_independent_raw_pixel_audit_matches_report_and_preserves_native_disagreement(actual_metadata):
    _,raw=actual_metadata
    report_path=ROOT/'evidence/06-real-metadata/factory-metadata-audit.json'
    if not report_path.is_file():pytest.skip('Factory audit report is not present')
    report=json.loads(report_path.read_text())
    assert report['metadata_sha256']==EXPECTED_SHA
    states={};first_inside=entries=exits=reentries=holds=disagree=0
    event_frames=[]
    for frame in raw['frames']:
        occupancy=0
        for obj in frame['objects']:
            if obj['class_id']!=0 or obj['label']!='person' or obj['confidence']<.5:continue
            b=obj['bbox'];x=b['left']+b['width']/2;y=b['top']+b['height']
            inside=806<=x<=1190 and 799<=y<=929
            occupancy+=inside
            track=obj['id'];previous=states.get(track)
            if inside:
                if previous is None:first_inside+=1;event_frames.append(frame['frame'])
                elif not previous[0]:
                    entries+=1;reentries+=int(previous[1]);event_frames.append(frame['frame'])
                else:holds+=1
            elif previous and previous[0]:exits+=1
            states[track]=(inside,inside or bool(previous and previous[1]))
        native=frame['analytics'][0]['roi_counts']['RestrictedZone']
        disagree+=int(native!=occupancy)
    assert (first_inside,entries,exits,reentries,holds)==(0,2,2,1,43)
    assert event_frames==[38,66]
    assert disagree==9
    assert report['computed_alerts']==first_inside+entries==2
    assert report['native_roi_geometry_comparison']['native_vs_actual_config_disagreeing_frames']==disagree
    assert report['track_gap_audit']['tracks_with_gaps']==4
    assert report['track_gap_audit']['total_gap_reappearances']==13
