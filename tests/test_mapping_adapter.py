"""Artificial source fixture; these keys make no claim about PipeGen output."""
import json
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from backend.adapters.field_mapping import FieldMappingParser, parse, pointer, timestamp, load_parser


def config():
    return {'version':1,'timestamp':{'path':'/capture/at'},'timestamp_format':'iso8601','camera_id':{'path':'/capture/camera'},'frame_width':{'path':'/capture/width'},'frame_height':{'path':'/capture/height'},'analytics_mode':'detections','detections':{'list_path':'/objects','class_name':{'path':'/kind'},'class_map':{'0':'person','2':'forklift'},'confidence':{'path':'/score'},'track_id':{'path':'/identity'},'bbox':{'path':'/rectangle','format':'xywh','units':'pixels'}}}


def raw():
    return {'capture':{'at':'2026-10-18T12:00:00+05:30','camera':'actual-camera','width':1000,'height':500},'objects':[{'kind':0,'score':.94,'identity':17,'rectangle':[250,100,200,300]}]}


def test_explicit_pixels_xywh_mapping():
    frame=FieldMappingParser(config())(raw())
    assert frame.timestamp==datetime(2026,10,18,6,30,tzinfo=timezone.utc)
    assert frame.camera_id=='actual-camera'
    assert frame.detections[0].bbox==(.25,.2,.45,.8)
    assert frame.detections[0].track_id=='17'
    assert frame.detections[0].class_name=='person'
    assert frame.fps is None and frame.gpu_name is None


@pytest.mark.parametrize('units,format,coords',[('pixels','xyxy',[250,100,450,400]),('normalized','xyxy',[.25,.2,.45,.8]),('normalized','xywh',[.25,.2,.2,.6])])
def test_bbox_conventions_explicit(units,format,coords):
    cfg=config();cfg['detections']['bbox'].update(units=units,format=format)
    sample=raw();sample['objects'][0]['rectangle']=coords
    assert FieldMappingParser(cfg)(sample).detections[0].bbox==(.25,.2,.45,.8)


def test_bbox_object_components():
    cfg=config();cfg['detections']['bbox']={'components':[{'path':'/rectangle/'+key} for key in ['left','top','width','height']],'format':'xywh','units':'pixels'}
    sample=raw();sample['objects'][0]['rectangle']={'left':250,'top':100,'width':200,'height':300}
    assert FieldMappingParser(cfg)(sample).detections[0].bbox==(.25,.2,.45,.8)


@pytest.mark.parametrize('missing',[True,False])
def test_missing_id_remains_none(missing):
    sample=raw()
    if missing: sample['objects'][0].pop('identity')
    else: sample['objects'][0]['identity']=None
    assert FieldMappingParser(config())(sample).detections[0].track_id is None


def test_track_sentinel_requires_explicit_config():
    sample=raw();sample['objects'][0]['identity']=-1
    cfg=config()
    assert FieldMappingParser(cfg)(sample).detections[0].track_id=='-1'
    cfg['detections']['missing_track_values']=[-1]
    assert FieldMappingParser(cfg)(sample).detections[0].track_id is None


@pytest.mark.parametrize('fmt,value',[('epoch_s',1792305000),('epoch_ms',1792305000000),('epoch_us','1792305000000000'),('epoch_ns','1792305000000000000')])
def test_epoch_units_explicit(fmt,value):
    assert timestamp(value,fmt)==datetime.fromtimestamp(1792305000,timezone.utc)


def test_subsecond_precision():
    assert timestamp('1000123456','epoch_ns')==datetime(1970,1,1,0,0,1,123,tzinfo=timezone.utc)


@pytest.mark.parametrize('value',['2026-10-18T12:00:00','not-a-timestamp',1792305000])
def test_iso_timestamp_no_guessing(value):
    with pytest.raises(ValueError):timestamp(value,'iso8601')


@pytest.mark.parametrize('fmt,value',[('epoch_s',True),('epoch_ms','NaN'),('epoch_ns','Infinity'),('epoch_s','1e99')])
def test_invalid_epoch_rejected(fmt,value):
    with pytest.raises(ValueError):timestamp(value,fmt)


def test_config_constants_are_explicit():
    cfg=config();cfg['camera_id']={'value':'fixed-camera'};cfg['frame_width']={'value':1000};cfg['frame_height']={'value':500};cfg['source_name']={'value':'Verified upstream camera'}
    assert FieldMappingParser(cfg)(raw()).source_name=='Verified upstream camera'


@pytest.mark.parametrize('mutation',[
    lambda c:c['detections']['bbox'].pop('units'),
    lambda c:c['detections']['bbox'].update(format='auto'),
    lambda c:c['camera_id'].update(value='ambiguous'),
    lambda c:c.update(guessed_schema=True),
    lambda c:c['detections']['bbox'].update(components=[{'value':0}]*4),
    lambda c:c['detections'].update(list_path='objects'),
    lambda c:c.update(native_events={'list_path':'/events','event_id':{'path':'/id'},'zone_id':{'path':'/zone'},'event_type':{'path':'/type'}}),
])
def test_ambiguous_or_unknown_config_rejected(mutation):
    cfg=config();mutation(cfg)
    with pytest.raises(ValidationError):FieldMappingParser(cfg)


@pytest.mark.parametrize('mutation',[
    lambda s:s['capture'].pop('at'),
    lambda s:s['objects'][0].update(kind=99),
    lambda s:s['objects'][0].update(score=94),
    lambda s:s['objects'][0].update(rectangle=[-1,0,100,100]),
    lambda s:s['objects'][0].update(rectangle=[0,0,0,100]),
    lambda s:s['objects'][0].update(rectangle=[0,0,float('nan'),100]),
    lambda s:s['objects'][0].update(rectangle=[True,0,100,100]),
    lambda s:s['capture'].update(width=True),
    lambda s:s['capture'].update(height='500'),
    lambda s:s.update(objects={}),
    lambda s:s.update(objects=[None]),
])
def test_malformed_source_fails_closed(mutation):
    sample=raw();mutation(sample)
    with pytest.raises((ValueError,ValidationError)):FieldMappingParser(config())(sample)


def test_empty_detections_valid_but_missing_collection_invalid():
    sample=raw();sample['objects']=[]
    assert FieldMappingParser(config())(sample).detections==[]
    sample.pop('objects')
    with pytest.raises(ValueError):FieldMappingParser(config())(sample)


def test_numeric_class_requires_map():
    cfg=config();cfg['detections'].pop('class_map')
    with pytest.raises(ValueError):FieldMappingParser(cfg)(raw())


def test_json_pointer_escaped_keys_and_array_indices():
    assert pointer({'a/b':{'~key':[{'id':17}]}},'/a~1b/~0key/0/id')==17
    with pytest.raises(ValueError):pointer({},'/bad~2key')
    with pytest.raises(ValueError):pointer([1],'/01')


def test_native_mapping_and_explicit_event_map():
    cfg=config();cfg['analytics_mode']='native';cfg.pop('detections')
    cfg['native_events']={'list_path':'/alerts','event_id':{'path':'/sequence'},'zone_id':{'path':'/configured_zone'},'track_id':{'path':'/tracked'},'event_type':{'path':'/action'},'event_type_map':{'ENTER':'zone_entry','EXIT':'zone_exit'}}
    sample=raw();sample['alerts']=[{'sequence':'id-1','configured_zone':'local-zone-id','action':'ENTER'}]
    result=FieldMappingParser(cfg)(sample)
    assert result.detections==[] and result.analytics_mode=='native'
    assert result.native_events[0].event_type=='zone_entry'
    assert result.native_events[0].track_id is None
    sample['alerts'][0]['action']='UNKNOWN'
    with pytest.raises(ValueError):FieldMappingParser(cfg)(sample)


def test_file_configured_callable(tmp_path,monkeypatch):
    file=tmp_path/'mapping.json';file.write_text(json.dumps(config()))
    monkeypatch.setenv('SENTINEL_FIELD_MAPPING',str(file));load_parser.cache_clear()
    assert parse(raw()).detections[0].track_id=='17'
    monkeypatch.delenv('SENTINEL_FIELD_MAPPING')
    with pytest.raises(ValueError,match='SENTINEL_FIELD_MAPPING'):parse(raw())


def test_no_source_provenance_override():
    sample=raw();sample.update(source='synthetic',synthetic=True)
    result=FieldMappingParser(config())(sample).model_dump()
    assert 'source' not in result and 'synthetic' not in result
