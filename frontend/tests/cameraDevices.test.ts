import test from 'node:test';import assert from 'node:assert/strict';
import {SimulatedUsbDevices,cameraHarnessEnabled} from '../src/cameraDevices.ts';
function captured(){const track=Object.assign(new EventTarget(),{readyState:'live',stop(){this.readyState='ended'}});const stream={getTracks:()=>[track],getVideoTracks:()=>[track]} as unknown as MediaStream;let releases=0;return {stream,track,get releases(){return releases},release:()=>{releases++;track.stop()}}}
test('camera harness is explicit localhost development only',()=>{
 assert.equal(cameraHarnessEnabled({hostname:'localhost',search:'?cameraTest=1',dev:true}),true);
 for(const context of [{hostname:'example.com',search:'?cameraTest=1',dev:true},{hostname:'localhost',search:'',dev:true},{hostname:'localhost',search:'?cameraTest=1',dev:false}])assert.equal(cameraHarnessEnabled(context),false);
});
test('app-owned permission denial and unavailable devices never request real capture',async()=>{
 let captures=0;const access=new SimulatedUsbDevices(async()=>{captures++;return captured()});
 access.setMode('permission_denied');await assert.rejects(access.getUserMedia({video:true}),{name:'NotAllowedError'});
 access.setMode('unavailable');assert.deepEqual(await access.enumerateDevices(),[]);await assert.rejects(access.getUserMedia({video:true}),{name:'NotFoundError'});assert.equal(captures,0);
});
test('device discovery, switch, disconnect, reconnect and clean release use the same adapter path',async()=>{
 const resources:ReturnType<typeof captured>[]=[];const selected:string[]=[];
 const access=new SimulatedUsbDevices(async(id)=>{selected.push(id);const value=captured();resources.push(value);return value});
 assert.equal((await access.enumerateDevices()).length,2);
 const first=await access.getUserMedia({video:{deviceId:{exact:'sim-usb-a'}}});let ended=0;resources[0].track.addEventListener('ended',()=>ended++);
 assert.equal(access.snapshot().liveTracks,1);access.disconnect();assert.equal(ended,1);assert.equal(access.snapshot().activeStreams,0);assert.equal(resources[0].releases,1);
 access.setMode('connected');const second=await access.getUserMedia({video:{deviceId:{exact:'sim-usb-b'}}});access.release(second);access.release(first);
 assert.deepEqual(selected,['sim-usb-a','sim-usb-b']);assert.equal(access.snapshot().liveTracks,0);assert.equal(access.snapshot().released,2);
});
test('camera permission resolving after stop/disposal releases its late media stream',async()=>{
 let resolve!:(value:ReturnType<typeof captured>)=>void;const wait=new Promise<ReturnType<typeof captured>>(yes=>resolve=yes);const access=new SimulatedUsbDevices(async()=>wait);
 const pending=access.getUserMedia({video:true});access.dispose();const resource=captured();resolve(resource);
 await assert.rejects(pending,{name:'AbortError'});assert.equal(resource.releases,1);assert.equal(access.snapshot().activeStreams,0);assert.equal(access.snapshot().liveTracks,0);
});

test('stop cancels an app-owned pending recorded camera resource request immediately',async()=>{
 let aborted=false;const access=new SimulatedUsbDevices(async(_device,signal)=>new Promise((_,reject)=>signal.addEventListener('abort',()=>{aborted=true;reject(new DOMException('Canceled','AbortError'))},{once:true})));
 const pending=access.getUserMedia({video:true});access.dispose();await assert.rejects(pending,{name:'AbortError'});assert.equal(aborted,true);assert.equal(access.snapshot().activeStreams,0);
});
