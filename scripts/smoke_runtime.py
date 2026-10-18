"""Exercise HTTP + WebSocket through Vite against a RUNNING synthetic backend.
Run: .venv/bin/python scripts/smoke_runtime.py
Creates clearly synthetic incident rows; never runs against live mode.
"""
import asyncio
import json
from datetime import datetime, timezone
from uuid import uuid4
import httpx
import websockets


async def main():
    base = 'http://127.0.0.1:5173'
    async with httpx.AsyncClient(base_url=base, timeout=10) as client:
        status = (await client.get('/api/status')).raise_for_status().json()
        if status['mode'] != 'synthetic':
            raise SystemExit('Refusing mutation: start SENTINEL_MODE=synthetic first')
        camera = 'smoke-' + uuid4().hex[:8]
        zone = (await client.post('/api/zones', json={
            'name': 'Synthetic runtime smoke zone', 'camera_id': camera,
            'polygon': [[.4,.2],[.9,.2],[.9,.95],[.4,.95]], 'severity': 'high',
        })).raise_for_status().json()
        try:
            async with websockets.connect('ws://127.0.0.1:5173/ws/live') as socket:
                async def ingest(x):
                    response = await client.post('/api/ingest/detections', json={
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'camera_id': camera, 'frame_width': 1280, 'frame_height': 720,
                        'detections': [{'track_id': 'runtime-test', 'class_name': 'person',
                                        'confidence': .96, 'bbox': [x,.2,x+.1,.8]}],
                    })
                    response.raise_for_status()
                await ingest(.1)
                await ingest(.5)
                await ingest(.5)
                async def receive_incident():
                    while True:
                        message = json.loads(await socket.recv())
                        if message.get('type') == 'incident' and message['payload']['camera_id'] == camera:
                            return message['payload']
                event = await asyncio.wait_for(receive_incident(), timeout=5)
                assert event['synthetic'] is True
                incidents = (await client.get('/api/incidents')).raise_for_status().json()
                matching = [i for i in incidents if i['camera_id'] == camera]
                assert len(matching) == 1, matching
                await ingest(.1)
                await ingest(.5)
                incidents = (await client.get('/api/incidents')).raise_for_status().json()
                assert len([i for i in incidents if i['camera_id'] == camera]) == 2
                response = await client.patch('/api/incidents/' + event['id'] + '/acknowledge', json={'acknowledged': True})
                assert response.raise_for_status().json()['acknowledged'] is True
                assert (await client.get('/api/health')).status_code == 200
                print('PASS: Vite HTTP proxy, WebSocket proxy, entry suppression, re-entry, persistence, acknowledgment, synthetic provenance')
        finally:
            (await client.delete('/api/zones/' + zone['id'])).raise_for_status()


if __name__ == '__main__':
    asyncio.run(main())
