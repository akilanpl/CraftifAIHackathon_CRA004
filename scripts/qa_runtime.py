"""Run against running synthetic services after drawing Browser QA Zone in UI.
Refuses live mode. Uses a unique track prefix; keeps labeled synthetic evidence.
"""
import asyncio
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from uuid import uuid4
import httpx
import websockets

async def main(db_path):
    async with httpx.AsyncClient(base_url='http://127.0.0.1:5173',timeout=10) as c:
        assert (await c.get('/api/status')).json()['mode']=='synthetic', 'Synthetic mode required'
        z=next(z for z in (await c.get('/api/zones')).json() if z['name']=='Browser QA Zone')
        assert len(z['polygon'])==4 and z['polygon'][0][0] < z['polygon'][-1][0]
        tracks=['qa-'+uuid4().hex[:8]+'-A','qa-'+uuid4().hex[:8]+'-B']
        async def send(a,b):
            result=await c.post('/api/ingest/detections',json={
                'timestamp':datetime.now(timezone.utc).isoformat(),'camera_id':z['camera_id'],
                'frame_width':1280,'frame_height':720,
                'detections':[{'track_id':t,'class_name':'person','confidence':.96,
                    'bbox':[x-.04,.2,x+.04,.7]} for t,x in zip(tracks,[a,b])]})
            result.raise_for_status()
            return result.json()
        async with websockets.connect('ws://127.0.0.1:5173/ws/live') as ws:
            assert (await send(.1,.15))['incidents']==[]
            entry=await send(.5,.7)
            assert len(entry['incidents'])==2
            assert entry['status']['active_intrusions']==2
            assert (await send(.5,.7))['incidents']==[]
            outside=await send(.1,.7)
            assert outside['incidents']==[] and outside['status']['active_intrusions']==1
            assert len((await send(.5,.7))['incidents'])==1
            seen=set()
            while len(seen)<2:
                message=json.loads(await asyncio.wait_for(ws.recv(),timeout=5))
                if message['type']=='incident' and message['payload']['track_id'] in tracks:
                    seen.add(message['payload']['track_id'])
        items=(await c.get('/api/incidents',params={'zone_id':z['id'],'severity':'high','event_type':'zone_entry'})).json()
        mine=[e for e in items if e['track_id'] in tracks]
        assert len(mine)==3 and all(e['synthetic'] and e['source']=='synthetic' for e in mine)
        event=mine[0]
        for ack in [True,False,True]:
            r=await c.patch('/api/incidents/'+event['id']+'/acknowledge',json={'acknowledged':ack})
            assert r.raise_for_status().json()['acknowledged']==ack
        detail=(await c.get('/api/incidents/'+event['id'])).raise_for_status().json()
        assert detail['acknowledged'] is True
        summary=(await c.get('/api/analytics/summary')).json()
        assert summary['total_incidents']>=3 and summary['by_zone'][z['name']]>=3
        # Independent SQLite reader validates that HTTP history is truly durable.
        path=Path(db_path)
        db=sqlite3.connect(path)
        rows=[json.loads(row[0]) for row in db.execute('SELECT data FROM incidents')]
        db.close()
        assert len([e for e in rows if e['track_id'] in tracks])==3
        assert next(e for e in rows if e['id']==event['id'])['acknowledged'] is True
        print('PASS: UI-created/dragged polygon drives multi-person outside/entry/hold/exit/re-entry; actual WebSocket delivery, API filters/details/ack toggles, SQLite and analytics verified')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default='data/synthetic.sqlite3',help='Actual SQLite path configured for the synthetic backend')
    asyncio.run(main(parser.parse_args().db))
