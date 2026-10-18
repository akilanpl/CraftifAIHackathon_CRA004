from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from .geometry import validate_polygon


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class ZoneInput(StrictModel):
    name: str = Field(min_length=1,max_length=100)
    camera_id: str = Field(default='cam-01',min_length=1,max_length=100)
    polygon: list[tuple[float,float]]
    severity: Literal['low','medium','high','critical'] = 'high'
    confidence_threshold: float = Field(default=.5,ge=0,le=1)
    debounce_frames: int = Field(default=1,ge=1,le=120)

    @field_validator('polygon')
    @classmethod
    def valid_polygon(cls, value):
        return validate_polygon(value)


class Zone(ZoneInput):
    id: str


class Detection(StrictModel):
    track_id: Optional[str] = Field(default=None,min_length=1,max_length=100)
    class_name: str = Field(min_length=1,max_length=100)
    confidence: float = Field(ge=0,le=1)
    bbox: tuple[float,float,float,float]

    @field_validator('track_id',mode='before')
    @classmethod
    def stringify_track(cls, value):
        return str(value) if isinstance(value,int) else value

    @field_validator('bbox')
    @classmethod
    def valid_bbox(cls, b):
        if not all(0 <= v <= 1 for v in b) or b[0] >= b[2] or b[1] >= b[3]:
            raise ValueError('bbox must be normalized [x1,y1,x2,y2] with positive width and height')
        return b


class NativeEvent(StrictModel):
    event_id: str = Field(min_length=1,max_length=200)
    zone_id: str = Field(min_length=1)
    track_id: Optional[str] = None
    event_type: Literal['zone_entry','zone_exit']
    confidence: Optional[float] = Field(default=None,ge=0,le=1)


class ReplayContext(StrictModel):
    session_id: str
    frame_index: int = Field(ge=0)
    pts_ns: int = Field(ge=0)
    source_id: int = Field(ge=0)
    original_track_ids: dict[str,str] = Field(default_factory=dict)
    raw_roi_counts: list[dict[str,int]] = Field(default_factory=list)


class Frame(StrictModel):
    timestamp: datetime
    timestamp_basis: Optional[Literal['replay_session_clock']] = None
    replay: Optional[ReplayContext] = None
    camera_id: str = Field(min_length=1,max_length=100)
    frame_width: int = Field(gt=0,le=32768)
    frame_height: int = Field(gt=0,le=32768)
    detections: list[Detection] = Field(default_factory=list,max_length=1000)
    native_events: list[NativeEvent] = Field(default_factory=list,max_length=1000)
    analytics_mode: Literal['detections','native'] = 'detections'
    source_name: Optional[str] = Field(default=None,max_length=200)
    fps: Optional[float] = Field(default=None,ge=0)
    inference_latency_ms: Optional[float] = Field(default=None,ge=0)
    gpu_name: Optional[str] = Field(default=None,max_length=200)
    video_url: Optional[str] = Field(default=None,max_length=2048)

    @field_validator('timestamp')
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None:
            raise ValueError('timestamp must include timezone')
        return value.astimezone(timezone.utc)

    @model_validator(mode='after')
    def native_mode_explicit(self):
        if self.native_events and self.analytics_mode != 'native':
            raise ValueError('native_events require analytics_mode=native to prevent double counting')
        ids = [d.track_id for d in self.detections if d.track_id is not None]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate track IDs within one camera frame')
        return self


class Acknowledge(StrictModel):
    acknowledged: bool = True
