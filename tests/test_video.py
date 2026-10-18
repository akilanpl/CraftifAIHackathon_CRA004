"""Tiny artificial MP4-shaped bytes test transport, not video decoding/evidence."""
import asyncio
import hashlib
import json
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request
from backend.main import create_app
from backend.video import ReplayVideo, ReplayTimeline


@pytest.fixture
def media(tmp_path):
    path=tmp_path/'recorded.mp4'
    data=b'\x00\x00\x00\x18ftypisom'+bytes(range(128))
    path.write_bytes(data)
    return path,data


def request(method='GET',range_value=None):
    return Request({'type':'http','method':method,'headers':[(b'range',range_value.encode())] if range_value else []})


async def response_bytes(response):
    chunks=[]
    async for chunk in response.body_iterator:
        chunks.append(chunk)
    return b''.join(chunks)


def test_full_video_bytes(media):
    path,data=media
    response=ReplayVideo(path).response(request())
    assert response.status_code==200
    assert response.headers['content-type']=='video/mp4'
    assert response.headers['accept-ranges']=='bytes'
    assert response.headers['content-length']==str(len(data))
    assert asyncio.run(response_bytes(response))==data


@pytest.mark.parametrize('header,expected_start,expected_end', [('bytes=0-9',0,9),('bytes=10-',10,139),('bytes=-8',132,139),('bytes=130-9999',130,139),('bytes=-9999',0,139)])
def test_ranges(media,header,expected_start,expected_end):
    path,data=media
    assert len(data)==140
    response=ReplayVideo(path).response(request(range_value=header))
    assert response.status_code==206
    assert response.headers['content-range']==f'bytes {expected_start}-{expected_end}/{len(data)}'
    assert asyncio.run(response_bytes(response))==data[expected_start:expected_end+1]


@pytest.mark.parametrize('header',['bytes=140-','bytes=10-9','bytes=-0','bytes=-','bytes=0-1,3-4','items=0-3','bytes=abc-def','bytes='+'9'*200+'-'])
def test_bad_or_unsatisfiable_range(media,header):
    path,data=media
    response=ReplayVideo(path).response(request(range_value=header))
    assert response.status_code==416
    assert response.headers['content-range']=='bytes */140'


def test_head(media):
    path,data=media
    response=ReplayVideo(path).response(request(method='HEAD'))
    assert response.status_code==200 and response.body==b''
    assert response.headers['content-length']=='140'
    response=ReplayVideo(path).response(request(method='HEAD',range_value='bytes=10-19'))
    assert response.status_code==206 and response.headers['content-length']=='10' and response.body==b''


def test_unconfigured_and_invalid_file_fail_closed(tmp_path,monkeypatch):
    monkeypatch.delenv('SENTINEL_REPLAY_VIDEO',raising=False)
    for path in [None,tmp_path/'missing.mp4']:
        video=ReplayVideo(path)
        assert not video.status()['available']
        with pytest.raises(HTTPException) as exc:video.response(request())
        assert exc.value.status_code==404
    path=tmp_path/'private.txt';path.write_bytes(b'secret')
    with pytest.raises(HTTPException):ReplayVideo(path).response(request())
    invalid=tmp_path/'invalid.mp4';invalid.write_bytes(b'not mp4')
    with pytest.raises(HTTPException):ReplayVideo(invalid).response(request())


def metadata(tmp_path):
    path=tmp_path/'actual-shaped-fixture.json'
    data={'frames':[{'frame':42+i,'source_id':0,'pts_ns':7000000000+i*16683333,'width':100,'height':50,'objects':[{'id':17,'class_id':0,'label':'person','confidence':.9,'bbox':{'left':25,'top':10,'width':20,'height':30}}],'analytics':[]} for i in range(2)]}
    path.write_text(json.dumps(data))
    return path


def test_readonly_timeline_original_pts_ids_and_hash(tmp_path,media,monkeypatch):
    monkeypatch.delenv('SENTINEL_REPLAY_VIDEO_PTS_OFFSET_NS',raising=False)
    path=metadata(tmp_path)
    before=path.read_bytes()
    payload=ReplayTimeline(path,'cam-01',ReplayVideo(media[0])).payload()
    assert payload['first_pts_ns']==7000000000
    assert payload['pts_offset_ns'] is None and not payload['timestamp_mapping_configured']
    assert payload['read_only'] and not payload['synthetic']
    assert payload['metadata_sha256']==hashlib.sha256(before).hexdigest()
    assert payload['frames'][0]['detections'][0]['track_id']=='17'
    assert payload['frames'][0]['detections'][0]['bbox']==[.25,.2,.45,.8]
    assert payload['frames'][0]['frame_index']==42
    assert path.read_bytes()==before


def test_explicit_offset_and_tolerance(media):
    status=ReplayVideo(media[0],offset_ns='7000000000',tolerance_ns=8350000).status()
    assert status['pts_offset_ns']==7000000000 and status['timestamp_mapping_configured']
    assert status['tolerance_ns']==8350000
    for bad in ['auto',True,1.2]:
        with pytest.raises(ValueError):ReplayVideo(media[0],offset_ns=bad)
    with pytest.raises(ValueError):ReplayVideo(media[0],tolerance_ns=-1)


def test_video_and_timeline_endpoints_readonly(tmp_path,media,monkeypatch):
    monkeypatch.setenv('SENTINEL_REPLAY_VIDEO_PTS_OFFSET_NS','0')
    path=metadata(tmp_path)
    app=create_app(tmp_path/'video.db',mode='replay',replay_path=path,replay_video_path=media[0])
    with TestClient(app) as client:
        before=client.get('/api/incidents').json()
        for _ in range(3):
            payload=client.get('/api/replay/timeline').json()
            assert payload['total_frames']==2 and payload['video_available']
            assert client.get('/api/replay/video',headers={'Range':'bytes=0-9'}).content==media[1][:10]
            assert client.get('/api/replay/video?path=/etc/passwd').content==media[1]
            assert client.head('/api/replay/video').headers['content-length']=='140'
        assert client.get('/api/incidents').json()==before==[]
        assert app.state.replay.state=='ready' and not app.state.engine.states
        assert client.get('/api/replay').json()['video']['available']
        assert client.get('/api/status').json()['replay']['video']['available']


@pytest.mark.parametrize('mode',['live','synthetic'])
def test_video_endpoints_preserve_mode_isolation(tmp_path,media,mode):
    with TestClient(create_app(tmp_path/(mode+'.db'),mode=mode,replay_video_path=media[0])) as client:
        assert client.get('/api/replay/video').status_code==409
        assert client.get('/api/replay/timeline').status_code==409
