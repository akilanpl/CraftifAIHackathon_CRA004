"""Replay genuine PipeGen frame exports. PTS is relative, never capture wall time."""
import asyncio
from datetime import datetime, timezone, timedelta
from functools import wraps
import json
import math
from pathlib import Path
import time
from uuid import uuid4
from pydantic import Field
from .models import StrictModel, Frame, Detection

DEFAULT_PATH = None

class ReplayStart(StrictModel):
    speed: float = Field(default=1, ge=.1, le=32)


def number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value):
        raise ValueError(name+' must be a finite number')
    return value


def integer(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value,int) or value < minimum:
        raise ValueError(name+' must be an integer >= '+str(minimum))
    return value


def load_export(path):
    """Validate the whole batch before modifying replay/engine/database state.

    Coordinates are not clipped or repaired. The observed source has no edge
    overshoots; later incompatible exports must be reviewed rather than guessed.
    Analytics counts are intentionally not interpreted as entry/exit events.
    """
    with Path(path).open(encoding='utf-8') as handle:
        data = json.load(handle, parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Nonfinite JSON number')))
    if not isinstance(data,dict) or not isinstance(data.get('frames'),list) or not data['frames']:
        raise ValueError('Expected nonempty PipeGen frames batch')
    frames, seen, last_pts, last_indices, tracks = [], {}, -1, {}, set()
    observations = 0
    for raw in data['frames']:
        if not isinstance(raw,dict):
            raise ValueError('Each frame must be an object')
        index = integer(raw['frame'],'frame')
        source = integer(raw['source_id'],'source_id')
        pts = integer(raw['pts_ns'],'pts_ns')
        if source>2**32-1 or pts>2**64-1 or index>2**63-1:
            raise ValueError('Source/index/PTS integer exceeds supported range')
        width, height = integer(raw['width'],'width',1), integer(raw['height'],'height',1)
        if max(width,height)>32768:
            raise ValueError('Frame dimensions exceed canonical limit')
        if pts < last_pts or pts <= seen.get(source,-1) or index <= last_indices.get(source,-1):
            raise ValueError('PTS must increase per source and be ordered globally; frame indexes must increase per source')
        # Canonical datetime resolution is microseconds. Reject loss of ordering.
        if source in seen and (pts-data['frames'][0]['pts_ns'])//1000 <= (seen[source]-data['frames'][0]['pts_ns'])//1000:
            raise ValueError('PTS frames collide at microsecond resolution')
        if pts-data['frames'][0]['pts_ns'] > 365*86400*10**9:
            raise ValueError('Replay duration exceeds one year')
        seen[source], last_pts, last_indices[source] = pts, pts, index
        objects = raw['objects']
        if not isinstance(objects,list) or len(objects)>1000:
            raise ValueError('objects must be an array with at most 1000 entries')
        detections, frame_tracks = [], set()
        for obj in objects:
            if not isinstance(obj,dict):
                raise ValueError('Each object must be an object')
            cid = integer(obj['class_id'],'class_id')
            label = obj['label']
            if not isinstance(label,str) or not label.strip():
                raise ValueError('Object label must be nonempty')
            person = label.strip().lower()=='person'
            if (cid==0) != person:
                raise ValueError('Person class_id/label disagreement')
            confidence = number(obj['confidence'],'confidence')
            if not 0<=confidence<=1:
                raise ValueError('Confidence must be in [0,1]')
            box = obj['bbox']
            left,top,bw,bh = [number(box[k],'bbox '+k) for k in ('left','top','width','height')]
            if left<0 or top<0 or bw<=0 or bh<=0 or left+bw>width or top+bh>height:
                raise ValueError('Bounding box outside the stated frame or nonpositive')
            # Only actual nonnegative integer tracker IDs are recognized. NVIDIA's
            # uint64 max, negative/missing IDs and unknown types remain untracked.
            raw_id = obj.get('id')
            track = str(raw_id) if type(raw_id) is int and 0<=raw_id<2**64-1 else None
            if not person:
                continue
            observations += 1
            if track is not None:
                if track in frame_tracks:
                    raise ValueError('Duplicate person tracker ID within one frame')
                frame_tracks.add(track)
                tracks.add((source,track))
            normalized=dict(track_id=track,class_name='person',confidence=confidence,
                            bbox=[left/width,top/height,(left+bw)/width,(top+bh)/height])
            Detection.model_validate(normalized)
            detections.append(normalized)
        analytics=raw.get('analytics',[])
        if not isinstance(analytics,list):
            raise ValueError('analytics must be an array')
        roi_counts=[]
        for item in analytics:
            if not isinstance(item,dict) or not isinstance(item.get('roi_counts',{}),dict):
                raise ValueError('Invalid analytics count record')
            counts=item.get('roi_counts',{})
            for key,value in counts.items():
                integer(value,'roi count')
            roi_counts.append(dict(counts))
        frames.append(dict(frame_index=index,source_id=source,pts_ns=pts,width=width,height=height,detections=detections,raw_roi_counts=roi_counts))
    return frames, observations, len(tracks)


def serialized_control(method):
    @wraps(method)
    async def wrapped(self,*args,**kwargs):
        async with self.control_lock:
            return await method(self,*args,**kwargs)
    return wrapped


class ReplayController:
    def __init__(self,path,camera,ingest,reset):
        if not isinstance(camera,str) or not camera.strip() or len(camera)>80:
            raise ValueError('Replay camera must be a nonempty string of at most 80 characters')
        self.path,self.camera,self.ingest,self.reset = Path(path) if path else None,camera,ingest,reset
        self.control_lock=asyncio.Lock()
        self.frames=[]
        self.person_observations=self.unique_track_ids=0
        self.state='unconfigured'
        self.error=None
        self.index=-1
        self.speed=1
        self.session_id=None
        self.task=None
        self.latest=None
        self.paused_at=None
        self.paused_seconds=0.
        self.generation=0
        try:
            if not self.path:
                raise ValueError('Set SENTINEL_REPLAY_PATH to an actual PipeGen metadata export')
            self.frames,self.person_observations,self.unique_track_ids=load_export(self.path)
            self.state='ready'
        except (OSError,ValueError,KeyError,TypeError,OverflowError) as exc:
            self.error=str(exc)

    def status(self):
        current=self.frames[self.index] if 0<=self.index<len(self.frames) else None
        return dict(configured=bool(self.frames),state=self.state,running=self.state=='running',
                    completed=self.state=='completed',paused=self.state=='paused',current_frame_index=self.index,
                    total_frames=len(self.frames),pts_ns=current['pts_ns'] if current else None,
                    first_pts_ns=self.frames[0]['pts_ns'] if self.frames else None,
                    last_pts_ns=self.frames[-1]['pts_ns'] if self.frames else None,speed=self.speed,
                    session_id=self.session_id,person_observations=self.person_observations,
                    unique_track_ids=self.unique_track_ids,source_path=self.path.name if self.path else None,
                    timestamp_basis='replay_session_clock',error=self.error)

    async def cancel(self):
        self.generation+=1
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task=None

    @serialized_control
    async def start(self,speed):
        if not self.path:
            raise ValueError('Set SENTINEL_REPLAY_PATH to an actual PipeGen metadata export')
        frames,observations,tracks=load_export(self.path)  # no mutation on invalid source
        await self.cancel()
        self.frames,self.person_observations,self.unique_track_ids=frames,observations,tracks
        self.index=-1
        self.speed=speed
        self.session_id=str(uuid4())
        self.origin=datetime.now(timezone.utc)
        self.monotonic_origin=time.monotonic()
        self.paused_at=None
        self.paused_seconds=0.
        self.state='running'
        self.error=None
        self.latest=None
        self.reset()
        self.task=asyncio.create_task(self.play(self.generation))
        return self.status()

    @serialized_control
    async def pause(self):
        if self.state!='running':
            raise ValueError('Only a running replay can be paused')
        self.paused_at=time.monotonic()
        self.state='paused'
        return self.status()

    @serialized_control
    async def resume(self):
        if self.state!='paused':
            raise ValueError('Only a paused replay can be resumed')
        self.paused_seconds+=time.monotonic()-self.paused_at
        self.paused_at=None
        self.state='running'
        return self.status()

    @serialized_control
    async def stop(self):
        await self.cancel()
        self.state='stopped'
        self.reset()
        self.latest=None
        return self.status()

    async def wait(self,offset,generation):
        # Absolute deadlines avoid accumulating ingest/render overhead per frame.
        # Every frame is delivered; if late, catch up without dropping evidence.
        while True:
            if generation!=self.generation:
                return False
            if self.state=='paused':
                await asyncio.sleep(.01)
                continue
            deadline=self.monotonic_origin+self.paused_seconds+offset/self.speed
            remaining=deadline-time.monotonic()
            if remaining<=0:
                await asyncio.sleep(0)  # permit pause/stop even during catch-up
                if generation!=self.generation:
                    return False
                if self.state=='running':
                    return True
                continue
            await asyncio.sleep(min(.01,remaining))

    async def play(self,generation):
        try:
            sources={f['source_id'] for f in self.frames}
            for index,raw in enumerate(self.frames):
                if not await self.wait((raw['pts_ns']-self.frames[0]['pts_ns'])/1e9,generation):
                    return
                self.index=index
                source=raw['source_id']
                detections=[]
                original_ids={}
                for d in raw['detections']:
                    d=dict(d)
                    if d['track_id'] is not None:
                        original=d['track_id']
                        d['track_id']=f'{self.session_id}:{source}:{original}'
                        original_ids[d['track_id']]=original
                    detections.append(d)
                context=dict(session_id=self.session_id,frame_index=raw['frame_index'],pts_ns=raw['pts_ns'],
                             source_id=source,original_track_ids=original_ids,raw_roi_counts=raw['raw_roi_counts'])
                frame=Frame(timestamp=self.origin+timedelta(microseconds=(raw['pts_ns']-self.frames[0]['pts_ns'])//1000),
                            camera_id=self.camera if len(sources)==1 else f'{self.camera}:{source}',
                            frame_width=raw['width'],frame_height=raw['height'],detections=detections,
                            source_name='Recorded PipeGen metadata replay',timestamp_basis='replay_session_clock',replay=context)
                result=await self.ingest(frame,'pipegen_replay')
                self.latest=result['frame']
            self.state='completed'
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.state='error'
            self.error=str(exc)
