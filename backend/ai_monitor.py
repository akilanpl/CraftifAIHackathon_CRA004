"""Independent optional AI monitoring. Never imports or writes V2 application state."""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime,timedelta,timezone
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import time
from typing import Literal,Optional
from uuid import UUID,uuid4
from fastapi import FastAPI,HTTPException,Request,WebSocket,WebSocketDisconnect
from pydantic import Field, PrivateAttr, model_validator
from .database import Database
from .engine import ZoneEngine
from .models import StrictModel,ZoneInput,Zone,Frame,Detection,Acknowledge

MAX_FRAME_BYTES=2*1024*1024
TRACK_RETENTION_SECONDS=3
SCENARIO=[None,.2,.6,.6,.6,.2,.6,.6,.2]


class SessionInput(StrictModel):
    source_type: Literal['simulation','virtual_video','uploaded_video','usb_camera']
    capture_origin: Optional[Literal['physical_camera','simulated_usb_camera','recorded_video','simulation_fixture']]=None
    _capture_origin_was_explicit: bool=PrivateAttr(default=False)
    name: str=Field(default='AI monitor session',min_length=1,max_length=100)
    polygon: list[tuple[float,float]]
    confidence_threshold: float=Field(default=.5,ge=0,le=1)

    @model_validator(mode='after')
    def validate_capture_origin(self):
        defaults={'simulation':'simulation_fixture','virtual_video':'recorded_video','uploaded_video':'recorded_video','usb_camera':'physical_camera'}
        self._capture_origin_was_explicit=self.capture_origin is not None
        if self.capture_origin is None:self.capture_origin=defaults[self.source_type]
        allowed={'simulation':{'simulation_fixture'},'virtual_video':{'recorded_video'},'uploaded_video':{'recorded_video'},'usb_camera':{'physical_camera','simulated_usb_camera'}}
        if self.capture_origin not in allowed[self.source_type]:
            raise ValueError('capture_origin does not match the selected source type')
        return self

    def zone(self):
        return ZoneInput(name='Restricted zone',camera_id='ai-camera',polygon=self.polygon,confidence_threshold=self.confidence_threshold)


class ZoneUpdate(StrictModel):
    polygon: list[tuple[float,float]]
    confidence_threshold: float=Field(default=.5,ge=0,le=1)
    name: str=Field(default='Restricted zone',min_length=1,max_length=100)


class StepInput(StrictModel):
    seq: Optional[int]=Field(default=None,ge=0)


class UnavailableDetector:
    def __init__(self,cause='Independent inference adapter is not configured'):
        self.cause=cause
    def status(self):
        return dict(available=False,cause=self.cause,engine=None)
    def detect(self,data):
        raise RuntimeError(self.cause)


def default_detector():
    try:
        return importlib.import_module('backend.independent_inference').IndependentDetector()
    except Exception:
        return UnavailableDetector('Independent inference dependencies or configuration are unavailable')


def iou(a,b):
    intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    area=lambda c:(c[2]-c[0])*(c[3]-c[1])
    union=area(a)+area(b)-intersection
    return intersection/union if union>0 else 0


class EstimatedTracker:
    """Bounded greedy IoU associations, not verified physical person identities."""
    def __init__(self):
        self.tracks={};self.next_id=0
    def update(self,detections,media_time):
        self.tracks={key:value for key,value in self.tracks.items() if media_time-value['time']<=TRACK_RETENTION_SECONDS and value['missed']<5}
        for value in self.tracks.values():value['missed']+=1
        available=set(self.tracks)
        output=[]
        for item in detections:
            d=Detection.model_validate({**item,'track_id':None}).model_dump(mode='json')
            if d['class_name'].lower()!='person':continue
            best=max(available,key=lambda key:iou(d['bbox'],self.tracks[key]['bbox']),default=None)
            if best is None or iou(d['bbox'],self.tracks[best]['bbox'])<.3:
                best='estimated-'+str(self.next_id);self.next_id+=1
            else:available.remove(best)
            self.tracks[best]=dict(bbox=d['bbox'],time=media_time,missed=0)
            d['track_id']=best;output.append(d)
        return output


class MonitorSession:
    def __init__(self,directory,config,recovered=False):
        self.directory=directory;self.config=dict(config)
        defaults={'simulation':'simulation_fixture','virtual_video':'recorded_video','uploaded_video':'recorded_video','usb_camera':'physical_camera'}
        self.config.setdefault('capture_origin',defaults[self.config['source_type']])
        self.config.setdefault('capture_origin_basis','source_type_default')
        self.id=config['id'];self.db=Database(directory/'monitor.sqlite3')
        self.media_clock=0.
        self.engine=ZoneEngine(self.db,stale_seconds=TRACK_RETENTION_SECONDS,clock=lambda:self.media_clock,visible_only=True)
        self.tracker=EstimatedTracker();self.clients=set();self.inflight=False;self.generation=0
        self.last_seq=config.get('last_seq',-1);self.last_media_time=config.get('last_media_time',-1.)
        self.state='stopped' if recovered else 'running'
        self.reason='Service restarted; create a new session to continue without duplicating old history' if recovered else None
        self.last_result=None;self.last_digest=None;self.simulation_index=config.get('simulation_index',0)
        self.processing_latency_ms=None;self.processing_fps=None
        self.transition_counts={key:int(config.get('transition_counts',{}).get(key,0)) for key in ('entries','exits','reentries')}
        self.ever_inside=set()
        self.persist()

    @property
    def simulated(self):return self.config['source_type']=='simulation'

    def capture_info(self):
        origin=self.config['capture_origin']
        return dict(capture_origin=origin,capture_origin_basis=self.config['capture_origin_basis'],capture_origin_verified=False,input_is_simulated=origin in ('simulated_usb_camera','simulation_fixture'),physical_camera_hardware_test='NOT TESTED')

    def persist(self):
        value={**self.config,'last_seq':self.last_seq,'last_media_time':self.last_media_time,'state':self.state,'transition_counts':self.transition_counts,'simulation_index':self.simulation_index}
        temp=self.directory/('session-'+str(uuid4())+'.tmp')
        try:
            with temp.open('x',encoding='utf-8') as handle:handle.write(json.dumps(value,indent=2))
            temp.replace(self.directory/'session.json')
        finally:
            temp.unlink(missing_ok=True)

    def status(self):
        with self.db.lock:
            incident_count=self.db.conn.execute('SELECT COUNT(*) FROM incidents').fetchone()[0]
        return dict(id=self.id,name=self.config['name'],source_type=self.config['source_type'],state=self.state,reason=self.reason,created_at=self.config['created_at'],provenance='SIMULATED_TEST_DATA' if self.simulated else 'independent_ai_inference',synthetic=self.simulated,tracking='fixture_ground_truth_ids' if self.simulated else 'experimental_iou_association',tracking_verified=False,tracking_note='Fixture IDs test business logic, not detector accuracy' if self.simulated else 'IDs are estimated IoU associations, not verified physical identities; occlusion or large motion can start a new ID',**self.capture_info(),last_seq=self.last_seq,last_media_time=self.last_media_time,processing_latency_ms=self.processing_latency_ms,processing_fps=self.processing_fps,active_intrusions=self.engine.occupancy,incident_count=incident_count,transition_counts=self.transition_counts,zone=self.db.zones()[0] if self.db.zones() else None,simulation_steps=len(SCENARIO),simulation_index=self.simulation_index)

    async def broadcast(self,kind,payload):
        for socket in list(self.clients):
            try:
                await asyncio.wait_for(socket.send_json(dict(type=kind,payload=payload)),timeout=1)
            except Exception:self.clients.discard(socket)

    async def process(self,detections,width,height,seq,media_time,digest,telemetry=None):
        if self.state!='running':raise HTTPException(409,'Session is paused or stopped')
        telemetry=telemetry or {}
        self.media_clock=media_time
        # Expiration means lost observation, never an observed physical exit.
        self.engine.expire()
        self.ever_inside.intersection_update(self.engine.states)
        before={key for key,value in self.engine.states.items() if value['inside']}
        observed_outside_before={key for key,value in self.engine.states.items() if value.get('observed_outside') and not value['inside']}
        stamp=datetime.fromisoformat(self.config['created_at'])+timedelta(seconds=media_time)
        frame=Frame(timestamp=stamp,camera_id=self.id,frame_width=width,frame_height=height,detections=detections)
        events,warnings=self.engine.process(frame,'SIMULATED_TEST_DATA' if self.simulated else 'independent_ai_inference',self.simulated)
        after={key for key,value in self.engine.states.items() if value['inside']}
        exits=len(before-after)
        reentries=sum(key in self.ever_inside for key in after-before)
        self.ever_inside|=after
        self.transition_counts['entries']+=len(events);self.transition_counts['exits']+=exits;self.transition_counts['reentries']+=reentries
        for event in events:
            event_key=(event['camera_id'],event['zone_id'],event['track_id'])
            event['entry_basis']='observed_outside_to_inside' if event_key in observed_outside_before else 'first_observed_inside'
            event.update(session_id=self.id,source_type=self.config['source_type'],**self.capture_info(),model_sha256=telemetry.get('model_sha256'),engine=telemetry.get('engine'),provenance='SIMULATED_TEST_DATA' if self.simulated else 'independent_ai_inference',media_time=media_time,seq=seq,timestamp_basis='session_origin_plus_media_time',tracking='fixture_ground_truth_ids' if self.simulated else 'experimental_iou_association')
            self.db.save_incident(event)
        self.last_seq=seq;self.last_media_time=media_time;self.last_digest=digest
        telemetry=telemetry or {}
        self.processing_latency_ms=telemetry.get('processing_latency_ms');self.processing_fps=telemetry.get('processing_fps')
        result=dict(type='frame',session_id=self.id,**self.capture_info(),seq=seq,media_time=media_time,timestamp=stamp.isoformat(),timestamp_basis='session_origin_plus_media_time',frame_width=width,frame_height=height,detections=[d.model_dump(mode='json') for d in frame.detections],incidents=events,warnings=warnings,provenance='SIMULATED_TEST_DATA' if self.simulated else 'independent_ai_inference',synthetic=self.simulated,transitions=dict(entries=len(events),exits=exits,reentries=reentries),status=self.status(),processing_latency_ms=self.processing_latency_ms,processing_fps=self.processing_fps,model_sha256=telemetry.get('model_sha256'),engine=telemetry.get('engine'))
        self.last_result=result;self.persist()
        await self.broadcast('frame',result)
        for event in events:await self.broadcast('incident',event)
        await self.broadcast('status',self.status())
        return result


def create_ai_app(data_dir=None,detector=None):
    root=Path(data_dir or os.getenv('SENTINEL_AI_DATA_DIR',str(Path(__file__).resolve().parents[1]/'data'/'ai-monitor'))).resolve()
    root.mkdir(parents=True,exist_ok=True)
    detector=detector or default_detector()
    sessions={};worker=asyncio.Lock()
    for directory in root.iterdir():
        try:
            if not directory.is_dir() or str(UUID(directory.name))!=directory.name:continue
            # Do not follow arbitrary state-directory symlinks outside the isolated root.
            if directory.is_symlink() or directory.resolve().parent!=root:continue
            if (directory/'session.json').is_symlink() or (directory/'monitor.sqlite3').is_symlink():continue
            if (directory/'monitor.sqlite3').exists() and (directory/'monitor.sqlite3').stat().st_nlink!=1:continue
            config=json.loads((directory/'session.json').read_text())
            if config.get('id')!=directory.name:continue
            sessions[directory.name]=MonitorSession(directory,config,recovered=True)
        except (OSError,ValueError,KeyError):continue

    @asynccontextmanager
    async def lifespan(app):
        yield
        for session in sessions.values():
            session.state='stopped';session.persist()
            for socket in list(session.clients):
                try:await socket.close()
                except Exception:pass
            session.db.conn.close()

    app=FastAPI(title='Hazard Zone Sentinel — Independent AI Monitor',lifespan=lifespan)
    app.state.sessions=sessions;app.state.worker=worker;app.state.detector=detector

    def get_session(session_id):
        if session_id not in sessions:raise HTTPException(404,'AI session not found')
        return sessions[session_id]

    def order(session,seq,media_time):
        if seq<0 or not math.isfinite(media_time) or not 0<=media_time<=86400*7:
            raise HTTPException(422,'seq must be nonnegative and media_time finite within seven days')
        if seq<session.last_seq or (seq>session.last_seq and media_time<=session.last_media_time):
            raise HTTPException(409,'Out-of-order or seeked frame; create a new session after seeking/restarting the source')
        if seq==session.last_seq and media_time!=session.last_media_time:
            raise HTTPException(409,'A sequence number cannot refer to another media timestamp')

    @app.get('/api/ai/status')
    async def status():
        return dict(service='independent_ai_monitor',inference=detector.status(),simulation_available=True,physical_camera_hardware_test='NOT TESTED',max_frame_bytes=MAX_FRAME_BYTES,max_detections_per_frame=128,max_active_sessions=8,worker_busy=worker.locked(),queue_capacity=0,upload_storage_enabled=False,upload_note='Browser-selected videos are sampled as JPEG frames; server-side upload storage is disabled until off-root storage is configured and verified')

    @app.get('/api/ai/sessions')
    async def list_sessions():return [session.status() for session in sessions.values()]

    @app.post('/api/ai/sessions',status_code=201)
    async def new_session(payload:SessionInput):
        try:zone=payload.zone()
        except ValueError as exc:raise HTTPException(422,str(exc)) from exc
        if sum(session.state!='stopped' for session in sessions.values())>=8:raise HTTPException(429,'Maximum eight active AI sessions; stop an existing session')
        identifier=str(uuid4());directory=root/identifier;directory.mkdir(mode=0o700)
        session=MonitorSession(directory,dict(id=identifier,name=payload.name,source_type=payload.source_type,capture_origin=payload.capture_origin,capture_origin_basis='client_declared' if payload._capture_origin_was_explicit else 'source_type_default',created_at=datetime.now(timezone.utc).isoformat()))
        session.db.save_zone(Zone(id=identifier+'-zone',**{**zone.model_dump(),'camera_id':identifier}).model_dump(mode='json'))
        sessions[identifier]=session
        return session.status()

    @app.get('/api/ai/sessions/{session_id}')
    async def session_info(session_id:str):return get_session(session_id).status()

    @app.put('/api/ai/sessions/{session_id}/zone')
    async def update_zone(session_id:str,payload:ZoneUpdate):
        session=get_session(session_id)
        if session.inflight:raise HTTPException(429,'A frame is still processing; retry zone change')
        if session.state=='stopped':raise HTTPException(409,'Stopped sessions retain their historical zone')
        try:zone=Zone(id=session_id+'-zone',camera_id=session_id,**payload.model_dump())
        except ValueError as exc:raise HTTPException(422,str(exc)) from exc
        session.db.save_zone(zone.model_dump(mode='json'));session.engine.clear_zone(zone.id)
        session.tracker=EstimatedTracker();session.ever_inside.clear()
        await session.broadcast('status',session.status())
        return session.status()

    @app.post('/api/ai/sessions/{session_id}/frames')
    async def frame_input(session_id:str,request:Request,seq:int,media_time:float):
        session=get_session(session_id);order(session,seq,media_time)
        if session.simulated:raise HTTPException(409,'Simulation fixtures use the explicitly labeled simulation endpoint')
        if session.state!='running':raise HTTPException(409,'Session is not running')
        if session.inflight or worker.locked():raise HTTPException(429,'Inference worker busy; drop this capture and send the latest frame later')
        if request.headers.get('content-type','').split(';')[0]!='image/jpeg':raise HTTPException(415,'Frames must be JPEG image/jpeg bytes')
        if not detector.status().get('available'):raise HTTPException(501,dict(message='Independent AI inference unavailable; no detections were generated',inference=detector.status()))
        session.inflight=True
        generation=session.generation
        await worker.acquire()
        detached=False
        try:
            data=bytearray()
            async for chunk in request.stream():
                if len(data)+len(chunk)>MAX_FRAME_BYTES:raise HTTPException(413,'JPEG frame exceeds 2 MiB')
                data.extend(chunk)
            if len(data)<4 or data[:2]!=b'\xff\xd8':raise HTTPException(422,'Empty or invalid JPEG frame')
            digest=hashlib.sha256(data).hexdigest()
            if seq==session.last_seq:
                if digest==session.last_digest and session.last_result:return session.last_result
                raise HTTPException(409,'Repeated sequence does not match the processed frame')
            inference_task=asyncio.create_task(asyncio.to_thread(detector.detect,bytes(data)))
            try:
                result=await asyncio.shield(inference_task)
            except asyncio.CancelledError:
                # Cancelling an HTTP request cannot stop an already running CPU call.
                # Retain the worker slot until that call actually finishes; its
                # abandoned result must never create an incident.
                detached=True
                def release_abandoned(task):
                    if not task.cancelled():task.exception()
                    session.inflight=False
                    worker.release()
                inference_task.add_done_callback(release_abandoned)
                raise
            except ValueError as exc:raise HTTPException(422,'Independent decoder rejected the image') from exc
            except Exception as exc:raise HTTPException(503,'Independent inference failed or is unavailable; no result was recorded') from exc
            if session.state!='running' or session.generation!=generation:raise HTTPException(409,'Session controls changed during inference; result discarded')
            if not isinstance(result,dict) or not isinstance(result.get('detections'),list) or len(result['detections'])>128:raise HTTPException(502,'Inference adapter returned an invalid bounded result')
            try:
                validated=[Detection.model_validate({**item,'track_id':None}).model_dump(mode='json') for item in result['detections']]
                Frame(timestamp=datetime.now(timezone.utc),camera_id=session_id,frame_width=result['width'],frame_height=result['height'],detections=validated)
                threshold=session.db.zones()[0]['confidence_threshold']
                confident=[item for item in validated if item['class_name'].lower()=='person' and item['confidence']>=threshold]
                detections=session.tracker.update(confident,media_time)
                # Validate before processing changes incident state.
                Frame(timestamp=datetime.now(timezone.utc),camera_id=session_id,frame_width=result['width'],frame_height=result['height'],detections=detections)
            except (ValueError,KeyError,TypeError) as exc:raise HTTPException(502,'Inference adapter result failed canonical validation') from exc
            return await session.process(detections,result['width'],result['height'],seq,media_time,digest,result)
        finally:
            if not detached:
                session.inflight=False;worker.release()

    @app.post('/api/ai/sessions/{session_id}/simulation/step')
    async def simulation_step(session_id:str,payload:StepInput=StepInput()):
        session=get_session(session_id)
        if not session.simulated:raise HTTPException(409,'This source is not SIMULATED TEST DATA')
        if session.inflight:raise HTTPException(429,'A simulation step is already in flight')
        seq=payload.seq if payload.seq is not None else session.last_seq+1
        if seq==session.last_seq and session.last_result:return session.last_result
        if seq!=session.last_seq+1:raise HTTPException(409,'Simulation sequence must advance exactly one step')
        if session.simulation_index>=len(SCENARIO):raise HTTPException(409,'Scenario complete; create a new simulation session to repeat')
        session.inflight=True
        try:
            x=SCENARIO[session.simulation_index];media_time=session.simulation_index*.25
            detections=[] if x is None else [dict(track_id='simulation-person-1',class_name='person',confidence=.99,bbox=[x-.05,.2,x+.05,.8])]
            result=await session.process(detections,1280,720,seq,media_time,'simulation-step-'+str(session.simulation_index))
            session.simulation_index+=1
            session.persist()
            result['status']=session.status();return result
        finally:session.inflight=False

    @app.post('/api/ai/sessions/{session_id}/{action}')
    async def control(session_id:str,action:str):
        session=get_session(session_id)
        if action not in ('pause','resume','stop'):raise HTTPException(404,'Unknown AI control')
        if session.state=='stopped' and action!='stop':raise HTTPException(409,'Stopped sessions cannot resume; create a new session')
        target={'pause':'paused','resume':'running','stop':'stopped'}[action]
        if session.state==target:return session.status()
        session.generation+=1
        session.state=target
        if action=='stop':
            session.engine.states.clear();session.engine.replay_visible.clear();session.tracker=EstimatedTracker()
            session.last_result=None;session.last_digest=None
        session.persist();await session.broadcast('status',session.status());return session.status()

    @app.get('/api/ai/sessions/{session_id}/incidents')
    async def incidents(session_id:str):return get_session(session_id).db.incidents()

    @app.patch('/api/ai/incidents/{incident_id}/acknowledge')
    async def acknowledge(incident_id:str,payload:Acknowledge):
        for session in sessions.values():
            event=next((event for event in session.db.incidents() if event['id']==incident_id),None)
            if event:
                event['acknowledged']=payload.acknowledged;session.db.save_incident(event)
                await session.broadcast('incident',event);return event
        raise HTTPException(404,'AI incident not found')

    @app.websocket('/ws/ai/{session_id}')
    async def live(socket:WebSocket,session_id:str):
        session=sessions.get(session_id)
        if session is None:await socket.close(code=1008);return
        await socket.accept();session.clients.add(socket)
        try:
            await socket.send_json(dict(type='status',payload=session.status()))
            if session.last_result:await socket.send_json(dict(type='frame',payload=session.last_result))
            while True:await socket.receive_text()
        except WebSocketDisconnect:pass
        finally:session.clients.discard(socket)

    return app
