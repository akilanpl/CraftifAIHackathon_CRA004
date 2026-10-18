"""Release documentation/availability contracts, using temporary databases only.

These are API transport checks. They neither execute a model nor contact the
running V2 service, camera, or preserved source databases.
"""
import asyncio
import importlib
import json
from pathlib import Path
import sys
import httpx
import pytest
from backend.ai_monitor import create_ai_app
from backend.models import Frame


@pytest.fixture
def primary_factory(tmp_path,monkeypatch):
    # Prevent backend.main's optional module-level app from adopting host runtime
    # configuration if this is the first import in a focused test process.
    monkeypatch.setenv('SENTINEL_MODE','live')
    monkeypatch.setenv('SENTINEL_DB_PATH',str(tmp_path/'import-only.sqlite3'))
    for key in ('SENTINEL_PROFILE_PATH','SENTINEL_DATASET_PROFILE','SENTINEL_PIPEGEN_PARSER','SENTINEL_JSONL_PATH','SENTINEL_REPLAY_PATH','SENTINEL_REPLAY_VIDEO'):
        monkeypatch.delenv(key,raising=False)
    fresh_import='backend.main' not in sys.modules
    module=importlib.import_module('backend.main')
    yield module.create_app
    if fresh_import:module.app.state.db.conn.close()


def test_final_api_health_does_not_imply_connected_vision_source(primary_factory,tmp_path):
    app=primary_factory(tmp_path/'health.sqlite3',mode='live')
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://isolated-test') as client:
            health=(await client.get('/api/health')).raise_for_status().json()
            status=(await client.get('/api/status')).raise_for_status().json()
        assert health['status']=='ok'
        assert status['connected'] is False and status['connection_state']=='disconnected'
        assert status['integration_status']=='not connected'
        assert status['gpu_name'] is None and status['fps'] is None and status['inference_latency_ms'] is None
        assert status['source_name'] is None and status['last_event_time'] is None
        assert status['configured_zones']==0 and status['active_intrusions']==0 and status['session_incidents']==0
    try:asyncio.run(exercise())
    finally:app.state.db.conn.close()


def test_final_documented_canonical_example_and_ingestion_routes_are_actual_contract(primary_factory,tmp_path):
    example=json.loads((Path(__file__).resolve().parents[1]/'examples/canonical-detection.json').read_text())
    validated=Frame.model_validate(example)
    assert len(validated.detections[0].bbox)==4
    assert all(0<=coordinate<=1 for coordinate in validated.detections[0].bbox)
    app=primary_factory(tmp_path/'schema.sqlite3',mode='live')
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://isolated-test') as client:
            schema=(await client.get('/openapi.json')).raise_for_status().json()
            for route in ('/api/ingest/detections','/api/ingest/pipegen'):
                assert 'post' in schema['paths'][route] and 'get' not in schema['paths'][route]
            assert set(schema['components']['schemas']['Frame']['required']) >= {'timestamp','camera_id','frame_width','frame_height'}
            canonical=(await client.post('/api/ingest/detections',json=example)).raise_for_status().json()
            assert canonical['frame']['source']=='canonical' and canonical['frame']['synthetic'] is False
            assert canonical['incidents']==[]  # No zone configured; example is not evidence.
            native=await client.post('/api/ingest/pipegen',json={})
            assert native.status_code==501 and isinstance(native.json()['detail'],str)
            assert 'not configured' in native.json()['detail']
            assert (await client.get('/api/incidents')).json()==[]
    try:asyncio.run(exercise())
    finally:app.state.db.conn.close()


class UnavailableByField:
    def __init__(self,field):self.field=field;self.calls=0
    def status(self):return {'available':False,'engine':'UNAVAILABLE_TEST_ADAPTER',self.field:'Deliberately unavailable release-contract fixture'}
    def detect(self,data):
        self.calls+=1
        raise AssertionError('Release availability contracts must not execute inference')


@pytest.mark.parametrize('reason_field',['reason','cause','error'])
def test_final_optional_ai_health_preserves_unavailability_reason_without_fake_results(tmp_path,reason_field):
    detector=UnavailableByField(reason_field)
    app=create_ai_app(tmp_path/'independent-only',detector)
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://isolated-test') as client:
            capability=(await client.get('/api/ai/status')).raise_for_status().json()
            assert capability['inference']['available'] is False
            assert capability['inference'][reason_field]=='Deliberately unavailable release-contract fixture'
            assert capability['simulation_available'] is True
            assert capability['physical_camera_hardware_test']=='NOT TESTED'
            session=(await client.post('/api/ai/sessions',json={'source_type':'usb_camera','capture_origin':'simulated_usb_camera','polygon':[[.4,.3],[.9,.3],[.9,.9],[.4,.9]]})).raise_for_status().json()
            result=await client.post(f"/api/ai/sessions/{session['id']}/frames?seq=1&media_time=0",content=b'\xff\xd8fixture\xff\xd9',headers={'content-type':'image/jpeg'})
            assert result.status_code==501
            assert result.json()['detail']['inference']['available'] is False
            assert reason_field in result.json()['detail']['inference']
            assert (await client.get(f"/api/ai/sessions/{session['id']}/incidents")).json()==[]
        assert detector.calls==0
    try:asyncio.run(exercise())
    finally:
        for session in app.state.sessions.values():session.db.conn.close()


def test_final_browser_local_video_contract_does_not_advertise_server_mp4_storage(tmp_path):
    detector=UnavailableByField('reason')
    app=create_ai_app(tmp_path/'browser-local-upload',detector)
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://isolated-test') as client:
            capability=(await client.get('/api/ai/status')).raise_for_status().json()
            assert capability['upload_storage_enabled'] is False
            assert 'Browser-selected videos' in capability['upload_note']
            session=(await client.post('/api/ai/sessions',json={'source_type':'uploaded_video','polygon':[[.4,.3],[.9,.3],[.9,.9],[.4,.9]]})).raise_for_status().json()
            wrong_media=await client.post(f"/api/ai/sessions/{session['id']}/frames?seq=1&media_time=0",content=b'not-an-uploaded-mp4',headers={'content-type':'video/mp4'})
            assert wrong_media.status_code==415
            assert 'JPEG' in wrong_media.json()['detail']
            assert session['capture_origin']=='recorded_video' and session['physical_camera_hardware_test']=='NOT TESTED'
        assert detector.calls==0
    try:asyncio.run(exercise())
    finally:
        for session in app.state.sessions.values():session.db.conn.close()
