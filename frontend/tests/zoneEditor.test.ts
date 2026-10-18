import test from 'node:test';
import assert from 'node:assert/strict';
import {canvasPoint, copyZoneDraft, moveVertex, newZoneDraft, polygonError, suggestedVertex, zoneDraftError, zonePayload, type ZoneDraft, type ZonePoint} from '../src/zoneEditor.ts';

const square: ZonePoint[] = [[.2,.2],[.8,.2],[.8,.8],[.2,.8]];
const valid = (): ZoneDraft => ({id:'original-zone',name:'  Restricted zone  ',camera_id:' warehouse-01 ',severity:'high',confidence_threshold:.5,debounce_frames:1,polygon:square.map(point=>[...point])});

test('existing zone drafts are deep copies and cancellation cannot change the source polygon',()=>{
  const original=valid(),draft=copyZoneDraft(original);
  draft.polygon[0][0]=.4;draft.name='Changed';
  assert.equal(original.polygon[0][0],.2);assert.equal(original.name,'  Restricted zone  ');
});
test('a new zone starts empty and uses the explicitly supplied camera',()=>{
  const draft=newZoneDraft('factory-02');
  assert.equal(draft.camera_id,'factory-02');assert.deepEqual(draft.polygon,[]);assert.equal(draft.id,undefined);
});
test('save payload trims labels, omits id and does not share polygon arrays',()=>{
  const draft=valid(),payload=zonePayload(draft);
  assert.equal(payload.name,'Restricted zone');assert.equal(payload.camera_id,'warehouse-01');assert.equal('id' in payload,false);
  payload.polygon[0][0]=.9;assert.equal(draft.polygon[0][0],.2);
});
test('valid clockwise, counterclockwise and concave polygons are accepted',()=>{
  assert.equal(polygonError(square),null);assert.equal(polygonError([...square].reverse()),null);
  assert.equal(polygonError([[.1,.1],[.9,.1],[.5,.5],[.9,.9],[.1,.9]]),null);
});
test('missing name and camera are rejected before any request can be created',()=>{
  assert.match(zoneDraftError({...valid(),name:' '})??'',/name/);
  assert.match(zoneDraftError({...valid(),camera_id:''})??'',/camera/);
});
test('invalid vertex counts, duplicate closing points and zero-area configurations are rejected',()=>{
  for(const points of [[],[[0,0],[1,1]],[[0,0],[.5,.5],[1,1]],[...square,[.2,.2]]])assert.notEqual(polygonError(points as ZonePoint[]),null);
});
test('bow ties and non-adjacent edge touches are rejected',()=>{
  assert.notEqual(polygonError([[.1,.1],[.9,.9],[.1,.9],[.9,.1]]),null);
  assert.notEqual(polygonError([[0,0],[1,0],[1,1],[.5,0],[0,1]]),null);
});
test('adjacent overlap and reversal are rejected but forward collinear edges are valid',()=>{
  assert.notEqual(polygonError([[0,0],[1,0],[.5,0],[1,1],[0,1]]),null);
  assert.equal(polygonError([[0,0],[.5,0],[1,0],[1,1],[0,1]]),null);
});
test('numeric coordinates fail closed for out-of-range and nonfinite values',()=>{
  for(const value of [-.001,1.001,NaN,Infinity]){
    const draft=valid();draft.polygon[0][0]=value;
    assert.match(polygonError(draft.polygon)??'',/between 0 and 1/);
    assert.throws(()=>zonePayload(draft));
  }
});
test('confidence and debounce match the backend bounds',()=>{
  for(const confidence of [-.1,1.1,NaN])assert.match(zoneDraftError({...valid(),confidence_threshold:confidence})??'',/Confidence/);
  for(const debounce of [0,121,1.5,NaN])assert.match(zoneDraftError({...valid(),debounce_frames:debounce})??'',/debounce/);
  assert.equal(zoneDraftError({...valid(),confidence_threshold:0,debounce_frames:120}),null);
});
test('pointer normalization adapts to size and clamps only pointer movement',()=>{
  assert.deepEqual(canvasPoint(350,200,{left:100,top:50,width:500,height:300}),[.5,.5]);
  assert.deepEqual(canvasPoint(600,350,{left:100,top:50,width:1000,height:600}),[.5,.5]);
  assert.deepEqual(canvasPoint(-10,999,{left:0,top:0,width:500,height:300}),[0,1]);
  assert.equal(canvasPoint(1,1,{left:0,top:0,width:0,height:300}),null);
});
test('moving a vertex leaves both the existing shape and other points independent',()=>{
  const moved=moveVertex(square,1,[.9,.25]);
  assert.deepEqual(moved[1],[.9,.25]);assert.deepEqual(square[1],[.8,.2]);
  moved[0][0]=.7;assert.equal(square[0][0],.2);
});
test('keyboard Add vertex provides a valid initial rectangle',()=>{
  const points:ZonePoint[]=[];
  for(let i=0;i<4;i++)points.push(suggestedVertex(points));
  assert.deepEqual(points,square);assert.equal(polygonError(points),null);
});
test('64 vertices are supported and the 65th is rejected',()=>{
  const points:ZonePoint[]=Array.from({length:64},(_,i)=>[.5+.4*Math.cos(i*2*Math.PI/64),.5+.4*Math.sin(i*2*Math.PI/64)]);
  assert.equal(polygonError(points),null);
  assert.match(polygonError([...points,[.5,.5]])??'',/at most 64/);
});
