import test from 'node:test';import assert from 'node:assert/strict';
import {monitorHealth,sourceCardIndex} from '../src/aiMonitorPresentation.ts';
const state={primaryBackendConnected:true,primarySocketConnected:true,checking:false,checked:true,serviceOnline:false,inferenceAvailable:false,serviceUncertain:false,source:'simulation' as const,cameraConnected:false,hasVideo:false,videoLoaded:false,sourceFailed:false,simulationAvailable:false,running:false,complete:false};
test('a healthy primary backend never makes the independent AI service healthy',()=>{
 const health=monitorHealth(state);assert.equal(health[0].value,'Connected');assert.equal(health[0].tone,'good');assert.equal(health[1].value,'Unavailable');assert.equal(health[1].tone,'warning');
});
test('service online and inference unavailable remain separate from checked, cached and pending states',()=>{
 assert.equal(monitorHealth({...state,serviceOnline:true})[1].value,'Inference unavailable');
 assert.equal(monitorHealth({...state,serviceOnline:true,inferenceAvailable:true})[1].value,'Inference ready');
 assert.equal(monitorHealth({...state,serviceOnline:true,inferenceAvailable:true,serviceUncertain:true})[1].tone,'warning');
 assert.equal(monitorHealth({...state,checking:true})[1].value,'Checking…');
 assert.equal(monitorHealth({...state,checked:false})[1].value,'Not checked');
});
test('source and session readiness never imply physical hardware verification or active inference',()=>{
 assert.equal(monitorHealth({...state,source:'usb_camera',cameraConnected:true})[2].value,'Camera connected');
 assert.match(monitorHealth({...state,source:'usb_camera',cameraConnected:true})[2].detail,/NOT TESTED/);
 assert.equal(monitorHealth({...state,simulationAvailable:true})[2].value,'Fixture ready');
 assert.equal(monitorHealth({...state,sessionState:'running'})[3].value,'Fixture session ready');
 assert.equal(monitorHealth({...state,source:'uploaded_video',sessionState:'running'})[3].value,'Ready · not sampling');
 assert.equal(monitorHealth({...state,running:true})[3].value,'Sampling frames');
 assert.equal(monitorHealth({...state,complete:true})[3].value,'Complete');
});
test('video source loading, missing file and decode errors have honest display states',()=>{
 assert.equal(monitorHealth({...state,source:'uploaded_video'})[2].value,'Select an MP4');
 assert.equal(monitorHealth({...state,source:'virtual_video',hasVideo:true})[2].value,'Loading video');
 assert.equal(monitorHealth({...state,source:'virtual_video',hasVideo:true,videoLoaded:true})[2].value,'Video loaded');
 assert.equal(monitorHealth({...state,source:'virtual_video',hasVideo:true,videoLoaded:true,sourceFailed:true})[2].value,'Video unavailable');
});
test('source cards support arrow, home and end selection without fake actions',()=>{
 assert.equal(sourceCardIndex('ArrowRight',3,4),0);assert.equal(sourceCardIndex('ArrowLeft',0,4),3);
 assert.equal(sourceCardIndex('ArrowDown',0,4),1);assert.equal(sourceCardIndex('ArrowUp',1,4),0);
 assert.equal(sourceCardIndex('Home',2,4),0);assert.equal(sourceCardIndex('End',0,4),3);assert.equal(sourceCardIndex('Escape',0,4),null);
});
