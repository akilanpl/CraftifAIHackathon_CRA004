"""Artificial assets verify profile safety; never factory judging evidence."""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.database import Database
from backend.main import create_app
from backend.profiles import DatasetProfile, file_sha256


def fixture(tmp_path,scene='factory',id='factory-test'):
    video=tmp_path/(id+'.mp4');video.write_bytes(b'\x00\x00\x00\x18ftypisom'+b'x'*100)
    metadata=tmp_path/(id+'.json')
    metadata.write_text(json.dumps({'frames':[{'frame':0,'source_id':0,'pts_ns':33366700,'width':100,'height':50,'objects':[],'analytics':[]}]}))
    manifest=dict(version=1,id=id,name='Artificial profile test',scene_type=scene,source_kind='recorded_pipegen',video_path=video.name,metadata_path=metadata.name,video_sha256=file_sha256(video),metadata_sha256=file_sha256(metadata),frame_width=100,frame_height=50,source_id=0,camera_id='factory-01',pts_offset_ns=33366700,pts_mapping_verified=True,pts_verification_note='Artificial unit fixture only',model_name='fixture-model',precision='FP16',zones=[dict(name='Configured factory zone',camera_id='factory-01',polygon=[[.5,.4],[.9,.4],[.9,.9],[.5,.9]])])
    file=tmp_path/(id+'-profile.json');file.write_text(json.dumps(manifest))
    return file,manifest,video,metadata


def test_verified_pair_and_public_no_paths(tmp_path):
    file,manifest,video,metadata=fixture(tmp_path)
    profile=DatasetProfile(file,'factory')
    assert profile.state=='READY' and profile.integrity()
    public=profile.public()
    assert public['verified'] and public['scene_type']=='factory'
    assert public['model_name']=='fixture-model'
    assert 'video_path' not in public and str(tmp_path) not in json.dumps(public)
    assert profile.metadata_path==metadata and profile.video_path==video


def test_missing_factory_never_uses_street_env(tmp_path,monkeypatch):
    file,manifest,video,metadata=fixture(tmp_path,scene='historical_street',id='street')
    monkeypatch.setenv('SENTINEL_REPLAY_PATH',str(metadata));monkeypatch.setenv('SENTINEL_REPLAY_VIDEO',str(video))
    profile=DatasetProfile(tmp_path/'absent-manifest.json','factory')
    assert profile.state=='PENDING' and profile.metadata_path is None
    assert profile.public()['scene_type']=='factory'
    assert profile.public()['model_name'] is None


@pytest.mark.parametrize('change',[
    lambda m:m.update(video_sha256='0'*64),
    lambda m:m.update(metadata_sha256='0'*64),
    lambda m:m.update(frame_width=999),
    lambda m:m.update(source_id=9),
    lambda m:m.update(scene_type='historical_street'),
    lambda m:m.update(pts_mapping_verified=False),
    lambda m:m.update(zones=[]),
    lambda m:m.update(id='../street'),
    lambda m:m.update(unknown_secret='should-not-leak'),
])
def test_invalid_manifest_fails_closed(tmp_path,change):
    file,manifest,_,_=fixture(tmp_path);change(manifest);file.write_text(json.dumps(manifest))
    profile=DatasetProfile(file,'factory')
    assert profile.state=='INVALID' and not profile.public()['verified']
    assert 'should-not-leak' not in json.dumps(profile.public())


def test_missing_asset_pending_and_duplicate_manifest_keys_invalid(tmp_path):
    file,manifest,video,_=fixture(tmp_path);video.unlink()
    assert DatasetProfile(file,'factory').state=='PENDING'
    file.write_text('{"id":"factory","id":"street"}')
    assert DatasetProfile(file,'factory').state=='INVALID'


def test_changed_verified_asset_invalidates_profile(tmp_path):
    file,_,video,_=fixture(tmp_path)
    profile=DatasetProfile(file,'factory')
    assert profile.integrity()
    video.write_bytes(video.read_bytes()+b'changed')
    assert not profile.integrity() and profile.public()['state']=='INVALID'


def test_database_isolation_restart_and_cross_profile_rejection(tmp_path):
    file,_,_,_=fixture(tmp_path)
    profile=DatasetProfile(file,'factory')
    path=tmp_path/'bound.db'
    db=Database(path);profile.bind_database(db);db.conn.close()
    db=Database(path);DatasetProfile(file,'factory').bind_database(db)
    assert db.incidents()==[]
    otherfile,_,_,_=fixture(tmp_path,scene='historical_street',id='street')
    with pytest.raises(ValueError,match='another dataset'):DatasetProfile(otherfile,'historical_street').bind_database(db)
    db.conn.close()


def test_nonempty_legacy_database_refused(tmp_path):
    file,_,_,_=fixture(tmp_path)
    db=Database(tmp_path/'oldstreet.db')
    db.save_zone({'id':'street-zone'})
    with pytest.raises(ValueError,match='nonempty unbound'):DatasetProfile(file,'factory').bind_database(db)
    db.conn.close()


def test_api_pending_factory_ignores_all_legacy_sources(tmp_path,monkeypatch):
    file,_,video,metadata=fixture(tmp_path,scene='historical_street',id='street')
    monkeypatch.setenv('SENTINEL_REPLAY_PATH',str(metadata));monkeypatch.setenv('SENTINEL_REPLAY_VIDEO',str(video))
    app=create_app(tmp_path/'pending.db',mode='replay',dataset_profile='factory',profile_path=tmp_path/'factory-absent.json')
    with TestClient(app) as client:
        assert client.get('/api/profile').json()['state']=='PENDING'
        assert client.get('/api/zones').json()==[]
        assert not client.get('/api/replay').json()['video']['available']
        assert client.get('/api/replay/timeline').status_code==409
        assert client.get('/api/replay/video').status_code==409
        assert client.post('/api/replay/start',json={}).status_code==409
        assert client.get('/api/incidents').json()==[]


def test_ready_api_profile_and_readonly_restart(tmp_path):
    file,_,_,_=fixture(tmp_path)
    path=tmp_path/'factory.db'
    for _ in range(2):
        with TestClient(create_app(path,mode='replay',profile_path=file,dataset_profile='factory')) as client:
            profile=client.get('/api/profile').json()
            assert profile['verified'] and profile['state']=='READY'
            assert client.get('/api/status').json()['profile']['id']=='factory-test'
            assert client.get('/api/replay/timeline').json()['profile']==profile
            zones=client.get('/api/zones').json()
            assert len(zones)==1 and zones[0]['id']=='factory-test-zone-1'
            assert zones[0]['polygon']==[[.5,.4],[.9,.4],[.9,.9],[.5,.9]]
            assert client.get('/api/incidents').json()==[]


def test_profile_rejects_mixed_live_mode(tmp_path):
    with pytest.raises(ValueError,match='require replay mode'):
        create_app(tmp_path/'mixed.db',mode='live',dataset_profile='factory')


def test_legacy_cannot_open_explicit_factory_database(tmp_path):
    file,_,_,_=fixture(tmp_path)
    db=Database(tmp_path/'factory-bound.db')
    DatasetProfile(file,'factory').bind_database(db)
    with pytest.raises(ValueError,match='profile-bound database'):DatasetProfile().bind_database(db)
    db.conn.close()


def test_changed_pair_same_profile_cannot_reuse_database(tmp_path):
    file,manifest,video,_=fixture(tmp_path)
    db=Database(tmp_path/'pair.db')
    DatasetProfile(file,'factory').bind_database(db)
    video.write_bytes(video.read_bytes()+b'new-video-pair')
    manifest['video_sha256']=file_sha256(video);file.write_text(json.dumps(manifest))
    changed=DatasetProfile(file,'factory')
    assert changed.state=='READY'
    with pytest.raises(ValueError,match='another dataset'):changed.bind_database(db)
    db.conn.close()
