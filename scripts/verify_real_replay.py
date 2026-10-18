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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('metadata', type=Path)
    parser.add_argument('--db', type=Path, required=True, help='New verification-only database; must not exist')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.db.exists():
        raise SystemExit('Refusing to reuse an existing verification database')
    original = args.metadata.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    raw = json.loads(original)
    app = create_app(args.db, mode='replay', replay_path=args.metadata)
    received_frames = received_people = 0
    received_incidents = []
    started = time.monotonic()
    with TestClient(app) as client:
        initial = client.get('/api/replay').raise_for_status().json()
        assert initial['configured'] and initial['total_frames'] == len(raw['frames'])
        with client.websocket_connect('/ws/live') as ws:
            session = client.post('/api/replay/start', json={'speed': 32}).raise_for_status().json()['session_id']
            # ticker broadcasts completion; every frame and incident must arrive first.
            for _ in range(len(raw['frames'])*4+20):
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
    assert hashlib.sha256(args.metadata.read_bytes()).hexdigest() == digest
    report = dict(source_sha256=digest, frames_received_over_websocket=received_frames,
        person_observations_received=received_people, unique_observed_track_ids=replay['unique_track_ids'],
        computed_incidents=len(events), entry_basis=dict(Counter(e.get('entry_basis','unspecified') for e in events)),
        distinct_incident_tracks=len({e['track_id'] for e in events}),
        final_visible_active_intrusions=status['active_intrusions'],
        sqlite_incidents=len(stored), acknowledge_persistence_verified=bool(events),
        input_unchanged=True, mode='REAL PIPEGEN REPLAY', video='metadata-only',
        session_id=session, elapsed_verification_seconds=round(time.monotonic()-started,3),
        note='Verification elapsed time is not inference performance; incident counts depend on the seeded polygon and session.')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
