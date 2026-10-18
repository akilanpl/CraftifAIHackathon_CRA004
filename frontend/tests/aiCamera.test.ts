import test from 'node:test';import assert from 'node:assert/strict';
import {FrameFlightGate,cameraFailure,releaseCamera,validateVideoFile} from '../src/aiCameraHelpers.ts';
test('one frame in flight and exact session, sequence and source media time correlate boxes',()=>{
 const gate=new FrameFlightGate();const frame={session_id:'upload',seq:4,media_time:2.333};const token=gate.begin(frame)!;
 assert.equal(gate.begin({...frame,seq:5}),null);assert.equal(gate.accepts(token,frame),true);
 assert.equal(gate.accepts(token,{...frame,session_id:'v2'}),false);assert.equal(gate.accepts(token,{...frame,seq:5}),false);
 assert.equal(gate.accepts(token,{...frame,media_time:2.5}),false);gate.finish(token);assert.ok(gate.begin({...frame,seq:5}));
});
test('stop/source change rejects late inference responses and permits a fresh session',()=>{
 const gate=new FrameFlightGate();const frame={session_id:'old',seq:1,media_time:0};const old=gate.begin(frame)!;gate.reset();
 assert.equal(gate.accepts(old,frame),false);const next=gate.begin({...frame,session_id:'new'})!;gate.finish(old);
 assert.equal(gate.accepts(next,{...frame,session_id:'new'}),true);
});
test('mock browser camera denial, missing hardware, disconnected resource release',async()=>{
 for(const name of ['NotAllowedError','NotFoundError','NotReadableError']){
  const mock={getUserMedia:async()=>{throw {name}}};await assert.rejects(mock.getUserMedia().catch(error=>{throw new Error(cameraFailure(error))}),/permission denied|No camera|cannot be read/);
 }
 let stopped=0;const track={stop:()=>stopped++,onended:()=>{throw new Error('cleanup must detach callback')}};
 releaseCamera({getTracks:()=>[track,track]});assert.equal(stopped,2);assert.equal(track.onended,null);releaseCamera(null);
});
test('uploaded video limits reject malformed, empty and oversized inputs without storing files',()=>{
 assert.equal(validateVideoFile({name:'warehouse.mp4',type:'video/mp4',size:100}),null);
 assert.match(validateVideoFile({name:'bad.txt',type:'text/plain',size:100})!,/MP4/);
 assert.match(validateVideoFile({name:'empty.mp4',type:'video/mp4',size:0})!,/empty/);
 assert.match(validateVideoFile({name:'huge.mp4',type:'video/mp4',size:251*1024*1024})!,/250/);
});

test('independent incident labels distinguish first observation from a verified observed crossing',async()=>{
 const {aiIncidentLabel}=await import('../src/aiCameraHelpers.ts');
 assert.equal(aiIncidentLabel('zone_entry','first_observed_inside'),'First observed inside');
 assert.equal(aiIncidentLabel('zone_entry','observed_outside_to_inside'),'Observed zone entry');
 assert.equal(aiIncidentLabel('zone_entry'),'zone entry');
});
