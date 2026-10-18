import test from 'node:test';
import assert from 'node:assert/strict';
import { incidentZoneOptions, normalizedPoint } from '../src/domain.ts';

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
