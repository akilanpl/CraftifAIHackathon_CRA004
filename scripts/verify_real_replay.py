"""Exercise actual export through HTTP/WebSockets/SQLite; never modifies its input."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.main import create_app
from backend.geometry import point_in_polygon
from backend.replay import load_export


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('metadata', type=Path)
    parser.add_argument('--db', type=Path, required=True, help='New verification-only database; must not exist')
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--profile',type=Path,help='Verified dataset manifest; uses its explicit zones and paired artifacts')
    args = parser.parse_args()
    if args.db.exists():
        raise SystemExit('Refusing to reuse an existing verification database')
    original = args.metadata.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    raw = json.loads(original)
    app_options = dict(mode='replay',replay_path=args.metadata)
    if args.profile:
        app_options.update(profile_path=args.profile,dataset_profile='factory')
    app = create_app(args.db, **app_options)
    zones = app.state.db.zones()
    audit_states = {}
    transitions = Counter({name:0 for name in ('first_observed_inside','observed_entries','observed_reentries','observed_exits','hold_observations')})
    native_comparison = Counter()
    parsed, _, _ = load_export(args.metadata)
    for frame in parsed:
        for zone in zones:
            geometry_count = 0
            for detection in frame['detections']:
                bbox = detection['bbox']
                inside = point_in_polygon(((bbox[0]+bbox[2])/2,bbox[3]),zone['polygon'])
                geometry_count += int(inside)
                if detection['track_id'] is None or detection['confidence'] < zone['confidence_threshold']:
                    continue
                key = (frame['source_id'],zone['id'],detection['track_id'])
                previous = audit_states.get(key)
                if inside:
                    if previous is None:
                        transitions['first_observed_inside'] += 1
                    elif not previous['inside']:
                        transitions['observed_entries'] += 1
                        if previous['ever_inside']:
                            transitions['observed_reentries'] += 1
                    else:
                        transitions['hold_observations'] += 1
                elif previous and previous['inside']:
                    transitions['observed_exits'] += 1
                audit_states[key] = dict(inside=inside,ever_inside=inside or bool(previous and previous['ever_inside']))
            # Native counts are occupancy, never events. Compare only an explicit matching ROI name.
            roi_name = 'restricted_zone' if 'restricted_zone' in zone['name'] else zone['name']
            native = [item[roi_name] for item in frame['raw_roi_counts'] if roi_name in item]
            if len(native)==1:
                native_comparison['compared_zone_frames'] += 1
                native_comparison['disagreeing_zone_frames'] += int(native[0]!=geometry_count)
                native_comparison['maximum_count_difference'] = max(native_comparison['maximum_count_difference'],abs(native[0]-geometry_count))
    received_frames = received_people = 0
    received_incidents = []
    started = time.monotonic()
    with TestClient(app) as client:
        if args.profile:
            timeline = client.get('/api/replay/timeline').raise_for_status().json()
            assert timeline['metadata_sha256']==digest, 'Profile metadata must match the explicit audit input'
        initial = client.get('/api/replay').raise_for_status().json()
        assert initial['configured'] and initial['total_frames'] == len(raw['frames'])
        with client.websocket_connect('/ws/live') as ws:
            session = client.post('/api/replay/start', json={'speed': 32}).raise_for_status().json()['session_id']
            # ticker broadcasts completion; every frame and incident must arrive first.
            for _ in range(sum(len(f['objects']) for f in raw['frames'])+len(raw['frames'])*2+20):
                message = ws.receive_json()
                payload = message['payload']
                if message['type'] == 'frame':
                    source = raw['frames'][received_frames]
                    assert payload['replay']['pts_ns'] == source['pts_ns']
                    assert payload['timestamp_basis'] == 'replay_session_clock'
                    assert payload['source'] == 'pipegen_replay' and not payload['synthetic']
                    people = [o for o in source['objects'] if o['class_id'] == 0 and o['label'] == 'person']
                    assert len(payload['detections']) == len(people)
                    for detection, obj in zip(payload['detections'], people):
                        box = obj['bbox']
                        expected = [box['left']/source['width'], box['top']/source['height'],
                            (box['left']+box['width'])/source['width'], (box['top']+box['height'])/source['height']]
                        assert detection['bbox'] == expected
                    received_frames += 1
                    received_people += len(people)
                elif message['type'] == 'incident':
                    received_incidents.append(payload)
                elif message['type'] == 'status' and payload.get('replay', {}).get('completed'):
                    break
            else:
                raise AssertionError('No replay completion status received')
        replay = client.get('/api/replay').raise_for_status().json()
        status = client.get('/api/status').raise_for_status().json()
        events = [e for e in client.get('/api/incidents').json() if e.get('replay', {}).get('session_id') == session]
        assert replay['completed'] and received_frames == len(raw['frames'])
        assert received_people == replay['person_observations']
        assert len(events) == len(received_incidents) == status['session_incidents']
        assert all(e['source'] == 'pipegen_replay' and not e['synthetic'] for e in events)
        if events:
            event = events[0]
            ack = client.patch('/api/incidents/'+event['id']+'/acknowledge', json={'acknowledged': True})
            assert ack.raise_for_status().json()['acknowledged']
    with sqlite3.connect(args.db) as db:
        stored = [json.loads(row[0]) for row in db.execute('SELECT data FROM incidents')]
    assert len(stored) == len(received_incidents)
    assert not events or any(e['id'] == events[0]['id'] and e['acknowledged'] for e in stored)
    # A fresh application instance must recover the same durable history and ack state.
    with TestClient(create_app(args.db,**app_options)) as recovered:
        restored = recovered.get('/api/incidents').raise_for_status().json()
        assert {e['id'] for e in restored} == {e['id'] for e in stored}
        assert not events or next(e for e in restored if e['id']==events[0]['id'])['acknowledged']
        for _ in range(2):
            with recovered.websocket_connect('/ws/live') as reconnect:
                assert reconnect.receive_json()['type']=='status'
                assert reconnect.receive_json()['type']=='zones'
        assert recovered.get('/api/incidents').json()==restored
    assert hashlib.sha256(args.metadata.read_bytes()).hexdigest() == digest
    report = dict(source_sha256=digest, frames_received_over_websocket=received_frames,
        person_observations_received=received_people, unique_observed_track_ids=replay['unique_track_ids'],
        computed_incidents=len(events), entry_basis=dict(Counter(e.get('entry_basis','unspecified') for e in events)),
        distinct_incident_tracks=len({e['track_id'] for e in events}),
        final_visible_active_intrusions=status['active_intrusions'],
        sqlite_incidents=len(stored), acknowledge_persistence_verified=bool(events),
        input_unchanged=True, restart_recovery_verified=True, websocket_reconnect_verified=True,
        observed_track_transitions=dict(transitions), native_roi_geometry_comparison=dict(native_comparison),
        comparison_note='Geometry occupancy uses all exported person boxes; incident transitions additionally apply confidence. Missing tracks never imply exits; counts do not establish physical identities.',
        mode='RECORDED PIPEGEN REPLAY', verification_scope='backend metadata analysis; no video decoding or inference',
        session_id=session, elapsed_verification_seconds=round(time.monotonic()-started,3),
        note='Verification elapsed time is not inference performance; incident counts depend on the seeded polygon and session.')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
