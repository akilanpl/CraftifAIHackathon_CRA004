import test from 'node:test';
import assert from 'node:assert/strict';
import { endpointAddress, ingestionBoundary, integrationInputLabel, integrationTimestamp, parseAIServiceHealth, parseV2ServiceHealth, readIntegrationJSON, type IntegrationStatus } from '../src/integrationHealth.ts';

const status: IntegrationStatus = {mode:'replay',integration_status:'recorded PipeGen metadata replay',source_name:null,last_event_time:null,fps:null,inference_latency_ms:null,gpu_name:null,errors:[]};

test('independent inference availability is parsed separately from V2 connectivity', () => {
  const value = parseAIServiceHealth({service:'independent_ai_monitor',inference:{available:true,engine:'onnxruntime_cpu',runtime_version:'1.31.0',providers:['CPUExecutionProvider']},worker_busy:false,physical_camera_hardware_test:'NOT TESTED'});
  assert.deepEqual(value,{available:true,engine:'onnxruntime_cpu',runtimeVersion:'1.31.0',providers:['CPUExecutionProvider'],reason:null,hardwareTest:'NOT TESTED',workerBusy:false});
  assert.equal(parseV2ServiceHealth({service:'independent_ai_monitor',status:'ok',mode:'live'}),null);
});
test('an available API can correctly report unavailable inference with actual reason or fallback cause', () => {
  const unavailable = parseAIServiceHealth({service:'independent_ai_monitor',inference:{available:false,engine:'onnxruntime_cpu',reason:'Model not configured',physical_camera_hardware_test:'NOT TESTED'}});
  assert.equal(unavailable?.available,false);assert.equal(unavailable?.reason,'Model not configured');
  const fallback = parseAIServiceHealth({service:'independent_ai_monitor',inference:{available:false,engine:null,cause:'Dependencies unavailable'}});
  assert.equal(fallback?.reason,'Dependencies unavailable');assert.equal(fallback?.hardwareTest,'Not reported');
});
test('wrong proxy targets and malformed health payloads never become a healthy independent service', () => {
  for (const value of [null,[],{},'html',{service:'Hazard Zone Sentinel',inference:{available:true}},{service:'independent_ai_monitor',inference:{}},{service:'independent_ai_monitor',inference:{available:'true'}}]) assert.equal(parseAIServiceHealth(value),null);
});
test('runtime facts are not fabricated when omitted and provider entries are validated', () => {
  const value = parseAIServiceHealth({service:'independent_ai_monitor',inference:{available:true,providers:['CPUExecutionProvider',null,42,'']}});
  assert.equal(value?.engine,null);assert.equal(value?.runtimeVersion,null);assert.equal(value?.workerBusy,null);assert.equal(value?.hardwareTest,'Not reported');
  assert.deepEqual(value?.providers,['CPUExecutionProvider']);
});
test('V2 health requires both expected service identity and ok status', () => {
  assert.deepEqual(parseV2ServiceHealth({service:'Hazard Zone Sentinel',status:'ok',mode:'replay'}),{mode:'replay'});
  assert.equal(parseV2ServiceHealth({service:'Hazard Zone Sentinel',status:'error',mode:'replay'}),null);
  assert.equal(parseV2ServiceHealth({status:'ok',mode:'replay'}),null);
  assert.equal(parseV2ServiceHealth({service:'Hazard Zone Sentinel',status:'ok'}),null);
});
test('input mode remains unknown without actual backend status', () => {
  assert.equal(integrationInputLabel(null,false,false),'Waiting for backend status');
  assert.equal(integrationInputLabel(status,true,false),'RECORDED PIPEGEN REPLAY');
  assert.equal(integrationInputLabel({...status,mode:'synthetic'},false,true),'SYNTHETIC TEST MODE');
  assert.equal(integrationInputLabel({...status,mode:'live'},false,false),'Live / production');
});
test('pending/invalid factory assets are not labeled ready replay while historical legacy remains explicit', () => {
  assert.equal(integrationInputLabel({...status,profile:{state:'PENDING',scene_type:'factory'}},true,false),'DATASET PROFILE · PENDING');
  assert.equal(integrationInputLabel({...status,profile:{state:'INVALID',scene_type:'factory'}},true,false),'DATASET PROFILE · INVALID');
  assert.equal(integrationInputLabel({...status,profile:{state:'LEGACY',scene_type:'historical_street'}},true,false),'RECORDED PIPEGEN REPLAY');
});
test('replay rejects both live ingestion routes and does not imply 501 or ready native parsing', () => {
  const boundary = ingestionBoundary(true,false);
  assert.match(boundary.canonical,/409/);assert.match(boundary.native,/409/);assert.match(boundary.note,/separate/);
  assert.doesNotMatch(boundary.note,/501/);
});
test('synthetic canonical provenance and native live-only restrictions remain distinct', () => {
  const boundary = ingestionBoundary(false,true);
  assert.equal(boundary.canonical,'Synthetic provenance');assert.match(boundary.native,/409/);assert.match(boundary.note,/requires live/);
  const live = ingestionBoundary(false,false);assert.match(live.note,/live mode/);assert.match(live.note,/501/);assert.match(live.note,/never changes/);
});
test('integration timestamp preserves absolute time and refuses ambiguous or impossible dates', () => {
  assert.equal(integrationTimestamp('2026-10-18T15:23:00+05:30'),'2026-10-18T09:53:00.000Z');
  assert.equal(integrationTimestamp('1970-01-01T00:00:00Z'),'1970-01-01T00:00:00.000Z');
  for (const value of [null,undefined,'not a date','2026-02-30T12:00:00Z','2026-10-18T12:00:00','2026-10-18T25:00:00Z']) assert.equal(integrationTimestamp(value),null);
});
test('copied endpoint URLs use the dashboard origin and correct secure WebSocket protocol', () => {
  assert.equal(endpointAddress('/api/ingest/detections','http://127.0.0.1:5173'),'http://127.0.0.1:5173/api/ingest/detections');
  assert.equal(endpointAddress('/api/ai/status','https://sentinel.example/workspace'),'https://sentinel.example/api/ai/status');
  assert.equal(endpointAddress('/ws/live','https://sentinel.example',true),'wss://sentinel.example/ws/live');
  assert.equal(endpointAddress('/ws/live','http://127.0.0.1:5173',true),'ws://127.0.0.1:5173/ws/live');
  assert.throws(() => endpointAddress('https://unrelated.example','https://sentinel.example'),/local API/);
  assert.throws(() => endpointAddress('/api/health','file:///tmp/index.html'),/HTTP/);
});
test('service check is a read-only noncached GET with the caller abort signal', async () => {
  const control = new AbortController();
  const fetcher: typeof fetch = async (input, init) => {
    assert.equal(input,'/api/ai/status');assert.equal(init?.method,'GET');assert.equal(init?.cache,'no-store');assert.equal(init?.signal,control.signal);assert.equal(init?.body,undefined);
    return new Response(JSON.stringify({service:'independent_ai_monitor',inference:{available:false}}),{status:200});
  };
  const value = await readIntegrationJSON('/api/ai/status',control.signal,fetcher);
  assert.equal(parseAIServiceHealth(value)?.available,false);
});
test('HTTP and invalid JSON failures remain explicit rather than reporting a healthy service', async () => {
  const signal = new AbortController().signal;
  await assert.rejects(readIntegrationJSON('/api/ai/status',signal,async () => new Response('unavailable',{status:503})),/HTTP 503/);
  await assert.rejects(readIntegrationJSON('/api/health',signal,async () => new Response('<html>wrong proxy target</html>',{status:200})),/Invalid JSON/);
});
test('aborted or disconnected checks propagate failure and never produce cached success', async () => {
  const control = new AbortController();control.abort();
  await assert.rejects(readIntegrationJSON('/api/ai/status',control.signal,async (_,init) => {
    assert.equal(init?.signal?.aborted,true);throw new DOMException('Aborted','AbortError');
  }),{name:'AbortError'});
  await assert.rejects(readIntegrationJSON('/api/health',new AbortController().signal,async () => {throw new TypeError('Failed to fetch');}),/Failed to fetch/);
});
