"""Explicit configurable metadata mapper. This does not describe PipeGen's schema.

SENTINEL_PIPEGEN_PARSER=backend.adapters.field_mapping:parse
SENTINEL_FIELD_MAPPING=/absolute/path/to/verified-mapping.json
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from functools import lru_cache
import json
import math
import os
from pathlib import Path
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from ..models import Frame


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class FieldRef(ConfigModel):
    path: Optional[str] = None
    value: Any = None

    @model_validator(mode='after')
    def explicit_selection(self):
        if ('path' in self.model_fields_set) == ('value' in self.model_fields_set):
            raise ValueError('A field must contain exactly one of path or value')
        if self.path is not None and not self.path.startswith('/'):
            raise ValueError('Paths must be explicit JSON Pointers starting with /')
        if 'path' in self.model_fields_set and self.path is None:
            raise ValueError('path cannot be null')
        return self


class BboxMapping(ConfigModel):
    path: Optional[str] = None
    components: Optional[list[FieldRef]] = None
    format: Literal['xyxy','xywh']
    units: Literal['normalized','pixels']

    @model_validator(mode='after')
    def unambiguous(self):
        if (self.path is None) == (self.components is None):
            raise ValueError('bbox requires exactly one of path or components')
        if self.path is not None:
            FieldRef(path=self.path)
        if self.components is not None and len(self.components) != 4:
            raise ValueError('bbox components must contain exactly four ordered references')
        return self


class DetectionMapping(ConfigModel):
    list_path: str
    class_name: FieldRef
    confidence: FieldRef
    bbox: BboxMapping
    track_id: Optional[FieldRef] = None
    class_map: Optional[dict[str,str]] = None
    missing_track_values: list[Any] = Field(default_factory=list)

    @model_validator(mode='after')
    def valid_path(self):
        FieldRef(path=self.list_path)
        return self


class NativeMapping(ConfigModel):
    list_path: str
    event_id: FieldRef
    zone_id: FieldRef
    event_type: FieldRef
    event_type_map: Optional[dict[str,Literal['zone_entry','zone_exit']]] = None
    track_id: Optional[FieldRef] = None
    confidence: Optional[FieldRef] = None
    missing_track_values: list[Any] = Field(default_factory=list)

    @model_validator(mode='after')
    def valid_path(self):
        FieldRef(path=self.list_path)
        return self


class MappingConfig(ConfigModel):
    version: Literal[1]
    timestamp: FieldRef
    timestamp_format: Literal['iso8601','epoch_s','epoch_ms','epoch_us','epoch_ns']
    camera_id: FieldRef
    frame_width: FieldRef
    frame_height: FieldRef
    analytics_mode: Literal['detections','native']
    detections: Optional[DetectionMapping] = None
    native_events: Optional[NativeMapping] = None
    source_name: Optional[FieldRef] = None
    fps: Optional[FieldRef] = None
    inference_latency_ms: Optional[FieldRef] = None
    gpu_name: Optional[FieldRef] = None
    video_url: Optional[FieldRef] = None

    @model_validator(mode='after')
    def exactly_one_analysis(self):
        if self.analytics_mode == 'detections' and (self.detections is None or self.native_events is not None):
            raise ValueError('detections mode requires detections mapping only')
        if self.analytics_mode == 'native' and (self.native_events is None or self.detections is not None):
            raise ValueError('native mode requires native_events mapping only')
        return self


_MISSING = object()


def pointer(data, path, optional=False):
    """RFC 6901 pointer subset: object keys and explicit array indexes, no wildcards."""
    current = data
    for encoded in path.split('/')[1:]:
        # Reject malformed escapes rather than interpret an ambiguous key.
        remainder = encoded.replace('~0','').replace('~1','')
        if '~' in remainder:
            raise ValueError('Malformed JSON Pointer escape in '+path)
        key = encoded.replace('~1','/').replace('~0','~')
        if isinstance(current,dict) and key in current:
            current = current[key]
        elif isinstance(current,list) and key.isdigit() and (key=='0' or not key.startswith('0')) and int(key)<len(current):
            current = current[int(key)]
        elif optional:
            return _MISSING
        else:
            raise ValueError('Required configured path is absent: '+path)
    return current


def read(data, ref, optional=False):
    if ref is None:
        return None
    value = pointer(data,ref.path,optional) if ref.path is not None else ref.value
    return None if value is _MISSING else value


def number(value,label):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError(label+' must be a finite JSON number')
    return value


def identifier(value,label,optional=False,missing_values=None):
    if optional and (value is None or value in (missing_values or [])):
        return None
    if isinstance(value,bool) or not isinstance(value,(str,int)) or not str(value).strip():
        raise ValueError(label+' must be a nonempty string or integer')
    return str(value)


def timestamp(value,format):
    if format == 'iso8601':
        if not isinstance(value,str):
            raise ValueError('ISO timestamp requires a string')
        try:
            result = datetime.fromisoformat(value.replace('Z','+00:00'))
        except ValueError as exc:
            raise ValueError('Invalid ISO timestamp') from exc
        if result.tzinfo is None:
            raise ValueError('ISO timestamp must include timezone; no timezone is guessed')
        return result.astimezone(timezone.utc)
    if isinstance(value,bool) or not isinstance(value,(int,float,str)):
        raise ValueError('Epoch timestamp requires a numeric value or numeric string')
    try:
        raw = Decimal(str(value))
        if not raw.is_finite():
            raise ValueError('Timestamp must be finite')
        divisors = {'epoch_s':1,'epoch_ms':1000,'epoch_us':1000000,'epoch_ns':1000000000}
        microseconds = int(raw*1000000/divisors[format])
        return datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(microseconds=microseconds)
    except (InvalidOperation,OverflowError,ValueError) as exc:
        raise ValueError('Invalid or out-of-range epoch timestamp') from exc


def mapped_string(value,mapping,label):
    if mapping is not None:
        key = identifier(value,label)
        if key not in mapping:
            raise ValueError(label+' has no explicit mapping: '+key)
        return mapping[key]
    if not isinstance(value,str) or not value.strip():
        raise ValueError(label+' requires a string, or an explicit value map')
    return value


class FieldMappingParser:
    def __init__(self,config):
        self.config = MappingConfig.model_validate(config)

    def __call__(self,raw):
        if not isinstance(raw,dict):
            raise ValueError('Configured parser accepts one JSON frame object per request')
        c = self.config
        width,height = read(raw,c.frame_width),read(raw,c.frame_height)
        if type(width) is not int or type(height) is not int or width<=0 or height<=0:
            raise ValueError('Configured frame dimensions must be positive JSON integers')
        result = dict(timestamp=timestamp(read(raw,c.timestamp),c.timestamp_format),camera_id=identifier(read(raw,c.camera_id),'camera_id'),frame_width=width,frame_height=height,analytics_mode=c.analytics_mode,detections=[],native_events=[])
        for field in ['source_name','fps','inference_latency_ms','gpu_name','video_url']:
            ref = getattr(c,field)
            if ref is not None:
                result[field] = read(raw,ref)  # Configured telemetry is required, never invented.
        if c.detections is not None:
            m = c.detections
            entries = pointer(raw,m.list_path)
            if not isinstance(entries,list) or len(entries)>1000:
                raise ValueError('Configured detections path must contain an array of at most 1000 objects')
            for entry in entries:
                if not isinstance(entry,dict):
                    raise ValueError('Every configured detection must be an object')
                b = m.bbox
                coords = pointer(entry,b.path) if b.path is not None else [read(entry,r) for r in b.components]
                if not isinstance(coords,(list,tuple)) or len(coords)!=4:
                    raise ValueError('Configured bbox requires four ordered coordinates')
                x,y,a,bottom = [number(v,'bbox coordinate') for v in coords]
                if b.format == 'xywh':
                    a,bottom = x+a,y+bottom
                if b.units == 'pixels':
                    x,a,y,bottom = x/width,a/width,y/height,bottom/height
                result['detections'].append(dict(track_id=identifier(read(entry,m.track_id,optional=True),'track_id',True,m.missing_track_values),class_name=mapped_string(read(entry,m.class_name),m.class_map,'class_name'),confidence=number(read(entry,m.confidence),'confidence'),bbox=[x,y,a,bottom]))
        if c.native_events is not None:
            m = c.native_events
            entries = pointer(raw,m.list_path)
            if not isinstance(entries,list) or len(entries)>1000:
                raise ValueError('Configured native events path must contain an array of at most 1000 objects')
            for entry in entries:
                if not isinstance(entry,dict):
                    raise ValueError('Every configured native event must be an object')
                confidence = read(entry,m.confidence,optional=True)
                result['native_events'].append(dict(event_id=identifier(read(entry,m.event_id),'event_id'),zone_id=identifier(read(entry,m.zone_id),'zone_id'),event_type=mapped_string(read(entry,m.event_type),m.event_type_map,'event_type'),track_id=identifier(read(entry,m.track_id,optional=True),'track_id',True,m.missing_track_values),confidence=None if confidence is None else number(confidence,'confidence')))
        return Frame.model_validate(result)


@lru_cache(maxsize=8)
def load_parser(filename):
    # Fixed per-process mapping: restart after reviewing and changing configuration.
    with Path(filename).open(encoding='utf-8') as source:
        return FieldMappingParser(json.load(source))


def parse(raw):
    filename = os.getenv('SENTINEL_FIELD_MAPPING')
    if not filename:
        raise ValueError('SENTINEL_FIELD_MAPPING must name an explicitly reviewed mapping JSON file')
    return load_parser(filename)(raw)
