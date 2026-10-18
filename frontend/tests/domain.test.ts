import test from 'node:test';
import assert from 'node:assert/strict';
import { incidentZoneOptions, normalizedPoint, pointInPolygon } from '../src/domain.ts';

test('incident filters retain a deleted zone and avoid duplicate options', () => {
  const options = incidentZoneOptions([{id:'active',name:'Renamed zone'}], [
    {zone_id:'active',zone_name:'Old name'},
    {zone_id:'deleted',zone_name:'Historical hazard'},
    {zone_id:'deleted',zone_name:'Historical hazard'},
  ]);
  assert.deepEqual(options, [{id:'active',name:'Renamed zone'},{id:'deleted',name:'Historical hazard (deleted zone)'}]);
});
test('polygon coordinates remain normalized when dragging beyond the frame', () => {
  const rect = {left:100,top:200,width:1002,height:502};
  assert.deepEqual(normalizedPoint(601,451,rect,1),[.5,.5]);
  assert.deepEqual(normalizedPoint(-20,900,rect,1),[0,1]);
  assert.deepEqual(normalizedPoint(101,201,rect,1),[0,0]);
  assert.deepEqual(normalizedPoint(1101,701,rect,1),[1,1]);
});
test('normalized polygon vertex coordinates adapt to a resized canvas', () => {
  assert.deepEqual(normalizedPoint(300,150,{left:0,top:0,width:600,height:300}),[.5,.5]);
  assert.deepEqual(normalizedPoint(600,300,{left:0,top:0,width:1200,height:600}),[.5,.5]);
});


test('recorded PipeGen evidence is distinct from live and synthetic input', async () => {
  const {sourceKind} = await import('../src/domain.ts');
  assert.equal(sourceKind('pipegen_replay',false), 'replay');
  assert.equal(sourceKind(undefined,false,'replay'), 'replay');
  assert.equal(sourceKind('pipegen',false), 'live');
  assert.equal(sourceKind('pipegen_replay',true), 'synthetic');
  assert.equal(sourceKind(undefined), 'canonical');
});
test('relative video PTS handles offsets, zero, and unavailable timestamps', async () => {
  const {relativePtsSeconds, formatRelativePts} = await import('../src/domain.ts');
  assert.equal(relativePtsSeconds(9_500_000_000,8_000_000_000),1.5);
  assert.equal(formatRelativePts(0,0),'0.00 s');
  assert.equal(relativePtsSeconds(1,2),0);
  assert.equal(formatRelativePts(undefined,0),'PTS unavailable');
  assert.equal(relativePtsSeconds(Infinity,0),null);
});

test('replay first-inside observations are never labeled as observed boundary crossings', async () => {
  const {incidentEventLabel} = await import('../src/domain.ts');
  assert.equal(incidentEventLabel('zone_entry','pipegen_replay',false,'first_observed_inside'),'Inside on first observation');
  assert.equal(incidentEventLabel('zone_entry','pipegen_replay',false,'observed_outside_to_inside'),'Observed zone entry');
  assert.equal(incidentEventLabel('zone_entry','pipegen_replay'),'Recorded zone alert (basis unavailable)');
  assert.equal(incidentEventLabel('zone_entry','pipegen'),'zone entry');
});
test('original replay IDs preserve raw ID zero and fall back without fabricating IDs', async () => {
  const {originalTrackId} = await import('../src/domain.ts');
  assert.equal(originalTrackId('session:0:0',{'session:0:0':'0'}),'0');
  assert.equal(originalTrackId('unmapped',{}),'unmapped');
  assert.equal(originalTrackId(null,{}),null);
});


test('recorded-video polygon highlights the same boundary-inclusive foot points as the backend', () => {
  const polygon=[[.55,.45],[.95,.45],[.95,.95],[.55,.95]];
  assert.equal(pointInPolygon([.7,.8],polygon),true);
  assert.equal(pointInPolygon([.55,.8],polygon),true);
  assert.equal(pointInPolygon([.4,.8],polygon),false);
  assert.equal(pointInPolygon([.8,.99],polygon),false);
});

test('profile labels never substitute street scene or model for a pending factory profile', async () => {
 const {replayProfileLabels,replayProfileKey}=await import('../src/domain.ts');
 const factory={id:'factory',name:'Factory safety · awaiting assets',state:'PENDING' as const,verified:false,model_name:null,precision:null};
 assert.deepEqual(replayProfileLabels(factory),{title:factory.name,model:'Model not reported',blocked:true});
 assert.equal(replayProfileLabels().title,'Recorded video · Safety monitoring');
 assert.equal(replayProfileLabels().model,'Model not reported');
 const historical={...factory,id:'historical-street',name:'Historical street clip',state:'READY' as const,model_name:'YOLOv8m',precision:'fp16',metadata_sha256:'old'};
 assert.equal(replayProfileLabels(historical).model,'YOLOv8m / FP16');
 assert.notEqual(replayProfileKey(factory),replayProfileKey(historical));
 assert.notEqual(replayProfileKey(historical),replayProfileKey({...historical,metadata_sha256:'replacement'}));
 assert.equal(replayProfileLabels({...factory,state:'INVALID'}).blocked,true);
 assert.equal(replayProfileLabels({...historical,state:'LEGACY',scene_type:'historical_street'}).blocked,false);
 assert.equal(replayProfileLabels({...factory,state:'LEGACY',scene_type:'factory'}).blocked,true);
});
