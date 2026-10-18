"""Entry state is scoped to camera/zone/track; lost state expires after timeout."""
import json
import time
from uuid import uuid4
from .geometry import point_in_polygon


class ZoneEngine:
    def __init__(self,db,stale_seconds=5,clock=time.monotonic):
        self.db,self.stale_seconds,self.clock = db,stale_seconds,clock
        self.states = {}
        self.last_timestamps = {}

    def expire(self):
        now = self.clock()
        self.states = {k:v for k,v in self.states.items() if now-v['seen'] <= self.stale_seconds}

    def clear_zone(self,zone_id):
        self.states = {k:v for k,v in self.states.items() if k[1] != zone_id}

    @property
    def occupancy(self):
        self.expire()
        return sum(1 for v in self.states.values() if v['inside'])

    def process(self,frame,source,synthetic=False):
        self.expire()
        previous = self.last_timestamps.get(frame.camera_id)
        if previous is not None and frame.timestamp <= previous:
            return [], ['Ignored duplicate or out-of-order frame timestamp']
        zones = {z['id']:z for z in self.db.zones() if z['camera_id'] == frame.camera_id}
        # Validate the complete batch before claiming IDs or changing state.
        if frame.analytics_mode == 'native' and any(e.zone_id not in zones for e in frame.native_events):
            raise ValueError('Native analytics references an unknown zone or wrong camera')
        self.last_timestamps[frame.camera_id] = frame.timestamp
        events,warnings = [],[]
        now = self.clock()

        def emit(zone,track,confidence):
            event = dict(id=str(uuid4()),timestamp=frame.timestamp.isoformat(),camera_id=frame.camera_id,zone_id=zone['id'],zone_name=zone['name'],track_id=track,confidence=confidence,event_type='zone_entry',severity=zone['severity'],acknowledged=False,source=source,synthetic=synthetic)
            self.db.save_incident(event)
            events.append(event)

        if frame.analytics_mode == 'native':
            for native in frame.native_events:
                key = json.dumps([source,frame.camera_id,native.event_id])
                if not self.db.claim_native(key):
                    continue
                zone = zones[native.zone_id]
                if native.confidence is not None and native.confidence < zone['confidence_threshold']:
                    continue
                already_inside = False
                if native.track_id is not None:
                    state_key = (frame.camera_id,zone['id'],native.track_id)
                    already_inside = self.states.get(state_key,{}).get('inside',False)
                    self.states[state_key] = dict(inside=native.event_type=='zone_entry',seen=now,count=1)
                if native.event_type == 'zone_entry' and not already_inside:
                    emit(zone,native.track_id,native.confidence)
            return events,warnings

        for detection in frame.detections:
            if detection.class_name.lower() != 'person':
                continue
            if detection.track_id is None:
                warnings.append('Person without track_id skipped: stable entry deduplication requires tracking')
                continue
            foot = ((detection.bbox[0]+detection.bbox[2])/2,detection.bbox[3])
            for zone in zones.values():
                key = (frame.camera_id,zone['id'],detection.track_id)
                state = self.states.setdefault(key,dict(inside=False,seen=now,count=0))
                state['seen'] = now
                if detection.confidence < zone['confidence_threshold']:
                    state['count'] = 0
                    continue  # Uncertain observation must not manufacture an exit/re-entry.
                inside = point_in_polygon(foot,zone['polygon'])
                if not inside:
                    state.update(inside=False,count=0)
                elif not state['inside']:
                    state['count'] += 1
                    if state['count'] >= zone.get('debounce_frames',1):
                        state['inside'] = True
                        emit(zone,detection.track_id,detection.confidence)
        return events,list(dict.fromkeys(warnings))
