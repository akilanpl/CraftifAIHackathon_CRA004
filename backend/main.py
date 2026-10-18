import asyncio
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
import os
from pathlib import Path
import time
from uuid import uuid4
from collections import Counter
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from .adapters.pipegen_adapter import PipeGenAdapter
from .database import Database
from .engine import ZoneEngine
from .models import Acknowledge, Frame, Zone, ZoneInput
from .websocket import ConnectionManager
from .replay import ReplayController, ReplayStart
from .video import ReplayVideo, ReplayTimeline


def create_app(db_path=None,mode=None,clock=time.monotonic,parser_path=None,replay_path=None,replay_video_path=None):
    mode = mode or os.getenv('SENTINEL_MODE','live')
    if mode not in ('live','synthetic','replay'):
        raise ValueError('SENTINEL_MODE must be live, synthetic or replay')
    default_path = Path(__file__).resolve().parent.parent / 'data' / ('synthetic.sqlite3' if mode == 'synthetic' else 'replay.sqlite3' if mode == 'replay' else 'sentinel.sqlite3')
    db = Database(db_path or os.getenv('SENTINEL_DB_PATH',str(default_path)),os.getenv('SENTINEL_JSONL_PATH'))
    replay_clock = [0.]
    engine = ZoneEngine(db,float('inf') if mode=='replay' else float(os.getenv('SENTINEL_TRACK_TIMEOUT','5')), (lambda: replay_clock[0]) if mode=='replay' else clock,visible_only=mode=='replay')
    manager = ConnectionManager()
    adapter = PipeGenAdapter(parser_path or os.getenv('SENTINEL_PIPEGEN_PARSER'))
    source_timeout = float(os.getenv('SENTINEL_SOURCE_TIMEOUT','10'))
    runtime = dict(last_received=None,last_event_time=None,source=None,source_name=None,fps=None,inference_latency_ms=None,gpu_name=None,video_url=None,session_incidents=0,errors=[],step=0)
    if mode == 'synthetic' and not db.zones():
        db.save_zone(Zone(id='synthetic-zone',name='Synthetic restricted area',camera_id='cam-01',polygon=[(.45,.35),(.9,.35),(.9,.9),(.45,.9)]).model_dump(mode='json'))

    replay = None
    replay_video = ReplayVideo(replay_video_path) if mode=='replay' else None
    replay_timeline = None
    if mode=='replay' and not db.zones():
        db.save_zone(Zone(id='replay-restricted-zone',name='PipeGen restricted_zone (replay polygon)',camera_id=os.getenv('SENTINEL_REPLAY_CAMERA','cam-01'),polygon=[(.55,.45),(.95,.45),(.95,.95),(.55,.95)]).model_dump(mode='json'))

    def status():
        connected = runtime['last_received'] is not None and clock()-runtime['last_received'] <= source_timeout
        result = dict(mode=mode,connected=connected,connection_state='connected' if connected else 'disconnected',integration_status='receiving metadata' if connected and runtime['source']=='pipegen' else ('adapter configured; awaiting metadata' if adapter.parser else 'not connected'),source_name=runtime['source_name'],last_event_time=runtime['last_event_time'],fps=runtime['fps'] if connected else None,inference_latency_ms=runtime['inference_latency_ms'] if connected else None,gpu_name=runtime['gpu_name'],video_url=runtime['video_url'] if connected else None,active_intrusions=engine.occupancy,session_incidents=runtime['session_incidents'],errors=runtime['errors'],configured_zones=len(db.zones()),source=runtime['source'])
        if mode=='replay':
            result.update(source='pipegen_replay',replay={**replay.status(),'video':replay_video.status()} if replay else None,integration_status='recorded PipeGen metadata replay',timestamp_basis='replay_session_clock')
        return result

    @asynccontextmanager
    async def lifespan(app):
        async def ticker():
            while True:
                await asyncio.sleep(1)
                await manager.broadcast('status',status())
        task = asyncio.create_task(ticker())
        yield
        if replay:
            await replay.cancel()
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        db.conn.close()

    app = FastAPI(title='Hazard Zone Sentinel',version='1.0.0',lifespan=lifespan)
    app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173','http://localhost:4173','http://127.0.0.1:4173'],allow_methods=['*'],allow_headers=['*'])
    app.state.db, app.state.engine, app.state.runtime = db,engine,runtime
    app.state.adapter = adapter

    @app.get('/api/health')
    async def health():
        return dict(status='ok',service='Hazard Zone Sentinel',mode=mode)

    @app.get('/api/status')
    async def get_status():
        return status()

    @app.get('/api/zones')
    async def zones():
        return db.zones()

    async def zones_changed():
        await manager.broadcast('zones',db.zones())
        await manager.broadcast('status',status())

    @app.post('/api/zones',status_code=201)
    async def create_zone(payload: ZoneInput):
        zone = Zone(id=str(uuid4()),**payload.model_dump()).model_dump(mode='json')
        db.save_zone(zone)
        await zones_changed()
        return zone

    @app.put('/api/zones/{zone_id}')
    async def update_zone(zone_id: str,payload: ZoneInput):
        if not any(z['id']==zone_id for z in db.zones()):
            raise HTTPException(404,'Zone not found')
        zone = Zone(id=zone_id,**payload.model_dump()).model_dump(mode='json')
        db.save_zone(zone)
        engine.clear_zone(zone_id)
        await zones_changed()
        return zone

    @app.delete('/api/zones/{zone_id}',status_code=204)
    async def delete_zone(zone_id: str):
        if not any(z['id']==zone_id for z in db.zones()):
            raise HTTPException(404,'Zone not found')
        db.delete_zone(zone_id)
        engine.clear_zone(zone_id)
        await zones_changed()

    @app.get('/api/incidents')
    async def incidents(severity: str=None,zone_id: str=None,event_type: str=None):
        return [e for e in db.incidents() if (not severity or e['severity']==severity) and (not zone_id or e['zone_id']==zone_id) and (not event_type or e['event_type']==event_type)]

    def find_incident(incident_id):
        event = next((e for e in db.incidents() if e['id']==incident_id),None)
        if event is None:
            raise HTTPException(404,'Incident not found')
        return event

    @app.get('/api/incidents/{incident_id}')
    async def incident(incident_id: str):
        return find_incident(incident_id)

    @app.patch('/api/incidents/{incident_id}/acknowledge')
    async def acknowledge(incident_id: str,payload: Acknowledge=Acknowledge()):
        event = find_incident(incident_id)
        event['acknowledged'] = payload.acknowledged
        db.save_incident(event)
        await manager.broadcast('incident',event)
        return event

    @app.get('/api/analytics/summary')
    async def analytics():
        items = db.incidents()
        dates = Counter(e['timestamp'][:10] for e in items)
        return dict(total_incidents=len(items),acknowledged=sum(e['acknowledged'] for e in items),by_severity=dict(Counter(e['severity'] for e in items)),by_zone=dict(Counter(e['zone_name'] for e in items)),trend=[dict(date=date,count=count) for date,count in sorted(dates.items())])

    async def ingest(frame,source):
        if frame.replay is not None:
            replay_clock[0] = frame.replay.pts_ns/1e9
        try:
            events,warnings = engine.process(frame,source,mode=='synthetic')
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from exc
        if warnings and warnings[0]=='Ignored duplicate or out-of-order frame timestamp':
            return dict(frame=None,incidents=[],warnings=warnings,status=status())
        runtime.update(last_received=clock(),last_event_time=frame.timestamp.isoformat(),source=source,source_name=frame.source_name or ('Synthetic metadata generator' if source=='synthetic' else 'Canonical metadata input' if source=='canonical' else 'PipeGen adapter'),fps=frame.fps,inference_latency_ms=frame.inference_latency_ms,gpu_name=frame.gpu_name,video_url=frame.video_url,errors=warnings)
        runtime['session_incidents'] += len(events)
        serialized = frame.model_dump(mode='json')
        serialized.update(source=source,synthetic=mode=='synthetic')
        await manager.broadcast('frame',serialized)
        for event in events:
            await manager.broadcast('incident',event)
        await manager.broadcast('status',status())
        return dict(frame=serialized,incidents=events,warnings=warnings,status=status())

    def reset_replay():
        engine.states.clear()
        engine.last_timestamps.clear()
        if engine.replay_visible is not None:
            engine.replay_visible.clear()
        runtime.update(last_received=None,last_event_time=None,session_incidents=0,errors=[])

    if mode=='replay':
        replay = ReplayController(replay_path or os.getenv('SENTINEL_REPLAY_PATH'),os.getenv('SENTINEL_REPLAY_CAMERA','cam-01'),ingest,reset_replay)
        replay_timeline = ReplayTimeline(replay.path,replay.camera,replay_video)
    app.state.replay = replay

    def require_replay():
        if replay is None:
            raise HTTPException(409,'Replay controls require SENTINEL_MODE=replay')
        return replay

    @app.get('/api/replay')
    async def replay_status():
        return {**require_replay().status(),'video':replay_video.status()}

    @app.api_route('/api/replay/video',methods=['GET','HEAD'])
    async def replay_video_stream(request: Request):
        require_replay()
        return replay_video.response(request)

    @app.get('/api/replay/timeline')
    async def replay_timeline_data():
        require_replay()
        return replay_timeline.payload()

    @app.post('/api/replay/start')
    async def replay_start(payload: ReplayStart=ReplayStart()):
        controller=require_replay()
        try:
            result=await controller.start(payload.speed)
        except (OSError,ValueError,KeyError,TypeError,OverflowError) as exc:
            raise HTTPException(422,'PipeGen replay rejected: '+str(exc)) from exc
        await manager.broadcast('status',status())
        return result

    @app.post('/api/replay/pause')
    async def replay_pause():
        try:
            result=await require_replay().pause()
        except ValueError as exc:
            raise HTTPException(409,str(exc)) from exc
        await manager.broadcast('status',status())
        return result

    @app.post('/api/replay/resume')
    async def replay_resume():
        try:
            result=await require_replay().resume()
        except ValueError as exc:
            raise HTTPException(409,str(exc)) from exc
        await manager.broadcast('status',status())
        return result

    @app.post('/api/replay/stop')
    async def replay_stop():
        result=await require_replay().stop()
        await manager.broadcast('status',status())
        return result

    @app.post('/api/ingest/detections')
    async def ingest_detections(payload: Frame):
        if mode=='replay':
            raise HTTPException(409,'Live ingestion is disabled during metadata replay')
        return await ingest(payload,'synthetic' if mode=='synthetic' else 'canonical')

    @app.post('/api/ingest/pipegen')
    async def ingest_pipegen(payload: dict):
        if mode in ('synthetic','replay'):
            raise HTTPException(409,'Direct PipeGen ingestion requires live mode; replay and synthetic modes reject mixed sources')
        try:
            frame = adapter.parse(payload)
        except NotImplementedError as exc:
            raise HTTPException(501,str(exc)) from exc
        except (ValidationError,ValueError,TypeError,KeyError) as exc:
            runtime['errors'] = ['PipeGen parser rejected metadata: '+str(exc)]
            raise HTTPException(422,runtime['errors'][0]) from exc
        except Exception as exc:
            runtime['errors'] = ['PipeGen parser failed: '+type(exc).__name__]
            raise HTTPException(502,runtime['errors'][0]) from exc
        return await ingest(frame,'pipegen')

    @app.post('/api/synthetic/step')
    async def synthetic_step():
        if mode != 'synthetic':
            raise HTTPException(409,'Synthetic generator requires SENTINEL_MODE=synthetic and a separate database')
        configured = db.zones()
        if not configured:
            raise HTTPException(409,'Create a zone before generating synthetic detections')
        zone = configured[0]
        # Search an interior point, so concave polygons remain testable.
        interior = next(((x/100,y/100) for y in range(1,100) for x in range(1,100) if point_in_zone((x/100,y/100),zone['polygon'])),None)
        if interior is None:
            raise HTTPException(409,'Zone is too small for the synthetic generator; use canonical test payloads')
        outside = next(((x,y) for x,y in [(0.01,.99),(.99,.99),(.01,.01),(.99,.01)] if not point_in_zone((x,y),zone['polygon'])),None)
        if outside is None:
            raise HTTPException(409,'Zone covers the synthetic canvas; use canonical test payloads')
        phase = runtime['step'] % 5
        runtime['step'] += 1
        foot = interior if phase in (1,2,4) else outside
        x,y = foot
        # Keep positive geometry even near frame boundaries.
        width = min(.1,x,1-x)
        frame = Frame(timestamp=datetime.now(timezone.utc),camera_id=zone['camera_id'],frame_width=1280,frame_height=720,detections=[dict(track_id='synthetic-person-1',class_name='person',confidence=.99,bbox=[x-width,max(0,y-.2),x+width,y])],source_name='SYNTHETIC TEST MODE — generated metadata')
        return await ingest(frame,'synthetic')

    @app.websocket('/ws/live')
    async def live(socket: WebSocket):
        await socket.accept()
        manager.clients.add(socket)
        try:
            await socket.send_json(dict(type='status',payload=status()))
            await socket.send_json(dict(type='zones',payload=db.zones()))
            if replay and replay.latest:
                await socket.send_json(dict(type='frame',payload=replay.latest))
            while True:
                await socket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            manager.clients.discard(socket)

    return app


from .geometry import point_in_polygon as point_in_zone
app = create_app()
