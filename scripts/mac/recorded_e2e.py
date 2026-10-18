"""Real HTTP/WebSocket application check using immutable recorded PipeGen data.

No inference runs here. All services, databases and logs belong to one temporary
QA directory. Existing production parsing, replay and incident logic are reused.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time

import httpx
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
METADATA = ROOT / 'evidence/06-real-metadata/warehouse-fp16-v2-metadata.json'
PROFILE = ROOT / 'examples/warehouse-profile.json'
EXPECTED_SHA = 'b88db711a3daf13d494c8c438ad8f13b6f5aa262d9d7402e621be83439c9ccce'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Service:
    def __init__(self, directory, name, module, settings, health):
        self.directory, self.name = directory, name
        self.module, self.settings, self.health = module, settings, health
        self.process = None

    def __enter__(self):
        # A pre-bound inherited descriptor avoids races with existing services.
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        self.port = listener.getsockname()[1]
        self.url = f'http://127.0.0.1:{self.port}'
        env = {k: v for k, v in os.environ.items() if not k.startswith(('SENTINEL_', 'AI_'))}
        env.update(self.settings)
        self.log = (self.directory / (self.name + '.log')).open('a')
        try:
            self.process = subprocess.Popen(
                [sys.executable, '-m', 'uvicorn', self.module, '--fd', str(listener.fileno())],
                cwd=ROOT, env=env, pass_fds=(listener.fileno(),), stdout=self.log, stderr=self.log)
        finally:
            listener.close()
        deadline = time.monotonic() + 15
        try:
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise RuntimeError(f'{self.name} stopped during startup')
                try:
                    if httpx.get(self.url + self.health, timeout=.5, trust_env=False).status_code == 200:
                        return self
                except httpx.TransportError:
                    pass
                time.sleep(.05)
            raise TimeoutError(f'{self.name} did not become healthy')
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *args):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.log.close()


def call(client, method, path, body=None, expected=200):
    response = client.request(method, path, json=body)
    assert response.status_code == expected, (method, path, response.status_code, response.text[:400])
    return response.json() if response.content else None


def wait_for(function, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = function()
        if result:
            return result
        time.sleep(.01)
    raise AssertionError('Timed out waiting for application state')


def run():
    assert digest(METADATA) == EXPECTED_SHA, 'Recorded metadata hash mismatch'
    profile = json.loads(PROFILE.read_text())
    protected = [METADATA, PROFILE, ROOT / 'evidence/04-tensorrt-fp16/warehouse-engine-summary.json',
                 ROOT / 'evidence/factory-export-audit.json']
    before = {str(p.relative_to(ROOT)): digest(p) for p in protected}
    with tempfile.TemporaryDirectory(prefix='sentinel-mac-e2e-') as temporary:
        directory = Path(temporary)
        warehouse_db = directory / 'warehouse.sqlite3'
        settings = {'SENTINEL_MODE': 'replay', 'SENTINEL_DB_PATH': str(warehouse_db),
                    'SENTINEL_REPLAY_PATH': str(METADATA), 'SENTINEL_REPLAY_CAMERA': profile['camera_id']}
        events = []
        # Metadata-only replay is supported by the existing application. Do not
        # fabricate a video or relabel its LEGACY profile as a verified pair.
        with ExitStack() as stack:
            primary = stack.enter_context(Service(directory, 'warehouse', 'backend.main:app', settings, '/api/health'))
            client = stack.enter_context(httpx.Client(base_url=primary.url, timeout=10, trust_env=False))
            assert call(client, 'GET', '/api/health')['mode'] == 'replay'
            status = call(client, 'GET', '/api/status')
            assert status['source'] == 'pipegen_replay'
            assert status['timestamp_basis'] == 'replay_session_clock'
            assert status['integration_status'] == 'recorded PipeGen metadata replay'
            assert status['gpu_name'] is None and status['fps'] is None
            zones = call(client, 'GET', '/api/zones')
            for zone in zones:
                call(client, 'DELETE', '/api/zones/' + zone['id'], expected=204)
            zone = call(client, 'POST', '/api/zones', profile['zones'][0], expected=201)
            assert zone['polygon'] == profile['zones'][0]['polygon']
            timeline = call(client, 'GET', '/api/replay/timeline')
            assert timeline['metadata_sha256'] == EXPECTED_SHA
            assert (timeline['total_frames'], timeline['person_observations'], timeline['unique_track_ids']) == (254, 522, 6)
            assert not timeline['video_available']
            ws_url = primary.url.replace('http:', 'ws:') + '/ws/live'
            with connect(ws_url, proxy=None) as ws:
                assert json.loads(ws.recv(timeout=5))['type'] == 'status'
                assert json.loads(ws.recv(timeout=5))['type'] == 'zones'
                done = threading.Event()
                errors = []

                def receive():
                    while not done.is_set():
                        try:
                            events.append(json.loads(ws.recv(timeout=.2)))
                        except TimeoutError:
                            continue
                        except Exception as exc:
                            errors.append(type(exc).__name__)
                            break

                reader = threading.Thread(target=receive)
                reader.start()
                try:
                    call(client, 'POST', '/api/replay/start', {'speed': 8})
                    wait_for(lambda: call(client, 'GET', '/api/replay')['current_frame_index'] >= 5)
                    paused = call(client, 'POST', '/api/replay/pause', {})
                    time.sleep(.08)
                    assert call(client, 'GET', '/api/replay')['current_frame_index'] == paused['current_frame_index']
                    call(client, 'POST', '/api/replay/resume', {})
                    final = wait_for(lambda: (s if (s := call(client, 'GET', '/api/replay'))['completed'] else None))
                    wait_for(lambda: len([e for e in events if e['type'] == 'frame']) == 254)
                    assert final['pts_ns'] == 10200000000
                    incidents = call(client, 'GET', '/api/incidents')
                    assert len(incidents) == 2
                    assert sorted(e['replay']['frame_index'] for e in incidents) == [38, 66]
                    assert sorted(e['replay']['pts_ns'] for e in incidents) == [1600000000, 2720000000]
                    assert all(e['source'] == 'pipegen_replay' and not e['synthetic'] and
                               e['timestamp_basis'] == 'replay_session_clock' and
                               e['entry_basis'] == 'observed_outside_to_inside' and
                               e['replay']['original_track_ids'][e['track_id']] == '0' for e in incidents)
                    identifier = incidents[0]['id']
                    assert call(client, 'GET', '/api/incidents/' + identifier) == incidents[0]
                    acknowledged = call(client, 'PATCH', '/api/incidents/' + identifier + '/acknowledge', {'acknowledged': True})
                    assert acknowledged['acknowledged']
                    wait_for(lambda: any(e['type'] == 'incident' and e['payload']['id'] == identifier and e['payload']['acknowledged'] for e in events))
                finally:
                    done.set()
                    reader.join(timeout=2)
                assert not errors and not reader.is_alive()
            frames = [e['payload'] for e in events if e['type'] == 'frame']
            source_frames = json.loads(METADATA.read_text())['frames']
            assert [f['replay']['frame_index'] for f in frames] == [f['frame'] for f in source_frames]
            assert [f['replay']['pts_ns'] for f in frames] == [f['pts_ns'] for f in source_frames]
            assert all(f['replay']['source_id'] == profile['source_id'] for f in frames)
            for delivered, original in zip(frames, source_frames):
                assert set(delivered['replay']['original_track_ids'].values()) == {str(o['id']) for o in original['objects'] if o['class_id'] == 0}
                assert (delivered['frame_width'], delivered['frame_height']) == (profile['frame_width'], profile['frame_height'])
            from datetime import datetime
            origin = datetime.fromisoformat(frames[0]['timestamp'])
            assert all(round((datetime.fromisoformat(f['timestamp'])-origin).total_seconds()*1e9) == f['replay']['pts_ns']-80000000 for f in frames)
            assert sum(len(f['detections']) for f in frames) == 522
            assert {original for f in frames for original in f['replay']['original_track_ids'].values()} == {'0','1','2','3','5','6'}
            # Observe exits/re-entry from delivered frames. The product persists
            # entry incidents; it does not expose exits as persisted incidents.
            from backend.geometry import point_in_polygon
            previous, seen_inside = {}, set()
            entries = exits = reentries = holds = 0
            for frame in frames:
                for detection in frame['detections']:
                    if detection['confidence'] < profile['zones'][0]['confidence_threshold']:
                        continue
                    track = frame['replay']['original_track_ids'][detection['track_id']]
                    box = detection['bbox']
                    inside = point_in_polygon(((box[0]+box[2])/2, box[3]), profile['zones'][0]['polygon'])
                    if inside and previous.get(track) is False:
                        entries += 1
                        reentries += track in seen_inside
                    elif not inside and previous.get(track) is True:
                        exits += 1
                    elif inside and previous.get(track) is True:
                        holds += 1
                    if inside:
                        seen_inside.add(track)
                    previous[track] = inside
            assert (entries, exits, reentries, holds) == (2, 2, 1, 43)
            assert len([e for e in events if e['type'] == 'incident' and not e['payload']['acknowledged']]) == 2
            with connect(ws_url, proxy=None) as reconnected:
                assert json.loads(reconnected.recv(timeout=5))['type'] == 'status'
                assert json.loads(reconnected.recv(timeout=5))['type'] == 'zones'
                assert json.loads(reconnected.recv(timeout=5))['payload']['replay']['frame_index'] == 253
            # Timeline reads/seek selection are visualization-only. No backend
            # seek API exists; explicit start means a new analysis, not playback.
            for index in (0, 66, 38, 253, 0):
                assert call(client, 'GET', '/api/replay/timeline')['frames'][index]['frame_index'] == index
            call(client, 'POST', '/api/replay/stop', {})
            saved = call(client, 'GET', '/api/incidents')
            assert len(saved) == 2
            summary = call(client, 'GET', '/api/analytics/summary')
            assert summary['total_incidents'] == 2 and summary['acknowledged'] == 1
            canonical = {k: v for k, v in frames[0].items() if k not in ('source', 'synthetic')}
            call(client, 'POST', '/api/ingest/detections', canonical, expected=409)
            call(client, 'POST', '/api/synthetic/step', {}, expected=409)
            call(client, 'POST', '/api/ingest/pipegen', {}, expected=409)
            synthetic = stack.enter_context(Service(directory, 'synthetic', 'backend.main:app',
                {'SENTINEL_MODE': 'synthetic', 'SENTINEL_DB_PATH': str(directory/'synthetic.sqlite3')}, '/api/health'))
            with httpx.Client(base_url=synthetic.url, trust_env=False) as fixture:
                for _ in range(3):
                    call(fixture, 'POST', '/api/synthetic/step', {})
                synthetic_incidents = call(fixture, 'GET', '/api/incidents')
                assert len(synthetic_incidents) == 1 and synthetic_incidents[0]['synthetic']
            ai = stack.enter_context(Service(directory, 'ai', 'backend.monitor_main:app',
                {'SENTINEL_AI_DATA_DIR': str(directory/'ai'), 'SENTINEL_AI_MODEL_PATH': str(directory/'absent.onnx')}, '/api/ai/status'))
            with httpx.Client(base_url=ai.url, trust_env=False) as independent:
                capability = call(independent, 'GET', '/api/ai/status')
                assert not capability['inference']['available']
                session = call(independent, 'POST', '/api/ai/sessions',
                    {'source_type': 'simulation', 'polygon': [[.45,.35],[.9,.35],[.9,.9],[.45,.9]]}, expected=201)
                for _ in range(9):
                    call(independent, 'POST', f"/api/ai/sessions/{session['id']}/simulation/step", {})
                result = call(independent, 'GET', f"/api/ai/sessions/{session['id']}")
                assert result['synthetic'] and result['incident_count'] == 2
                assert result['transition_counts'] == {'entries': 2, 'exits': 2, 'reentries': 1}
            assert call(client, 'GET', '/api/incidents') == saved
            ai.process.terminate()
            ai.process.wait(timeout=8)
            assert call(client, 'GET', '/api/health')['status'] == 'ok'
            assert call(client, 'GET', '/api/incidents') == saved
        # Restart the existing backend against this QA database, not a new analysis.
        with Service(directory, 'recovered', 'backend.main:app', settings, '/api/health') as recovered:
            with httpx.Client(base_url=recovered.url, trust_env=False) as client:
                assert call(client, 'GET', '/api/incidents') == saved
                assert call(client, 'GET', '/api/analytics/summary') == summary
                assert call(client, 'GET', '/api/replay')['state'] == 'ready'
        with sqlite3.connect(warehouse_db) as db:
            assert db.execute('SELECT COUNT(*) FROM incidents').fetchone()[0] == 2
        after = {str(p.relative_to(ROOT)): digest(p) for p in protected}
        assert before == after
        return {'status': 'PASS', 'scope': 'RECORDED METADATA REPLAY; no new NVIDIA inference',
                'platform': platform.system(), 'architecture': platform.machine(),
                'metadata_sha256': EXPECTED_SHA, 'frames': 254, 'person_observations': 522,
                'track_ids': 6, 'entry_incidents': entries, 'observed_exits': exits,
                'observed_reentries': reentries, 'suppressed_holds': holds,
                'websocket_frames': len(frames), 'acknowledgment_persisted_after_restart': True,
                'timeline_reads_and_stop_preserve_history': True, 'source_isolation': 'PASS',
                'independent_service_failure_isolation': 'PASS', 'protected_hashes': after,
                'browser': {'status': 'NOT_RUN', 'reason': 'Separate browser smoke verification required'}, 'video_synchronization': 'NOT_RETESTED; source MP4 unavailable',
                'cpu_inference': 'NOT_RUN; local model unavailable', 'temporary_services_and_databases': 'cleaned'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = run()
    rendered = json.dumps(report, indent=2) + '\n'
    if args.output:
        args.output.write_text(rendered)
    print(rendered)
