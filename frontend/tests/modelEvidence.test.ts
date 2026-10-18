import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {accuracyReviewState,copyEvidenceJson,evidenceNumber,measuredRange,warehouseMetrics} from '../src/modelEvidence.ts';
const read=(path:string)=>JSON.parse(readFileSync(new URL(`../../${path}`,import.meta.url),'utf8'));
const warehouse=read('evidence/04-tensorrt-fp16/warehouse-engine-summary.json');
const historical=read('evidence/04-tensorrt-fp16/measured-engine-summary.json');
const cpu=read('evidence/independent-ai/cpu-runtime-validation.json');
const evaluation=read('evidence/evaluation/independent-detection-evaluation.json');

test('warehouse cards use verified source values and keep engine throughput distinct from FPS',()=>{
 assert.equal(warehouse.engine_bytes,52_792_260);assert.equal(warehouse.reported_power.power_accuracy_w,5);
 assert.equal(evidenceNumber(warehouse.engine_bytes),'52,792,260');
 const metrics=warehouseMetrics(warehouse);
 assert.deepEqual(metrics.map(metric=>metric.value),['5.28244','6.19475','188.877','135.222']);
 assert.equal(metrics[2].unit,'inferences/s');assert.match(metrics[2].scope,/not video FPS/);
 assert.match(metrics[3].scope,/±5 W/);assert.equal(warehouse.power_watts_verified,null);
 assert.equal(warehouse.reported_power.independently_measured_by_this_audit,false);
});
test('historical and independent CPU evidence remain separate measured samples',()=>{
 assert.equal(historical.engine_bytes,52_730_564);assert.equal(historical.measured_gpu_compute_ms,4.94176);
 assert.equal(historical.measured_end_to_end_engine_ms,5.84506);assert.notEqual(historical.measured_gpu_compute_ms,warehouse.measured_gpu_compute_ms);
 assert.equal(cpu.frames.length,6);assert.equal(measuredRange(cpu.frames.map((frame:{processing_latency_ms:number})=>frame.processing_latency_ms)),'592.41–673.77');
 assert.equal(measuredRange(cpu.frames.map((frame:{processing_fps:number})=>frame.processing_fps)),'1.48–1.69');
 assert.equal(cpu.model.engine,'onnxruntime_cpu');assert.equal(cpu.physical_camera_hardware_test,'NOT TESTED');
});
test('accuracy state remains gated for incomplete human annotation exports',()=>{
 assert.equal(accuracyReviewState(evaluation).label,'PENDING HUMAN REVIEW');
 assert.equal(accuracyReviewState({formal_metrics_available:true,image_count:41,human_reviewed_image_count:1}).complete,false);
 assert.equal(accuracyReviewState({formal_metrics_available:false,image_count:41,human_reviewed_image_count:41}).complete,false);
 assert.equal(accuracyReviewState({formal_metrics_available:true,image_count:0,human_reviewed_image_count:0}).complete,false);
 assert.equal(accuracyReviewState({formal_metrics_available:true,image_count:41,human_reviewed_image_count:41}).complete,true);
});
test('missing or nonfinite measurements never become zero benchmarks',()=>{
 for(const value of [null,undefined,NaN,Infinity,'5',false])assert.equal(evidenceNumber(value,3),'Not reported');
 assert.equal(evidenceNumber(0,3),'0.000');assert.equal(measuredRange([undefined,NaN]),'Not reported');
 assert.equal(measuredRange([1,1]),'1.00');
});
test('copy source JSON preserves exact bytes, power uncertainty and null measurement scope',async()=>{
 let copied='';const original=JSON.stringify(warehouse);
 await copyEvidenceJson(warehouse,{writeText:async text=>{copied=text}});
 assert.equal(JSON.parse(copied).engine_bytes,52_792_260);assert.equal(JSON.parse(copied).reported_power.power_accuracy_w,5);
 assert.equal(JSON.parse(copied).power_watts_verified,null);assert.equal(JSON.stringify(warehouse),original);
});
test('copy failure remains explicit when clipboard is unavailable or permission denied',async()=>{
 await assert.rejects(copyEvidenceJson(warehouse),/Clipboard access is unavailable/);
 await assert.rejects(copyEvidenceJson(warehouse,{writeText:async()=>{throw new Error('Permission denied')}}),/Permission denied/);
});

test('source JSON links replace blocked data navigation with a released browser blob URL',async()=>{
 const {evidenceSourceUrl}=await import('../src/modelEvidence.ts');let created:Blob|undefined;const released:string[]=[];
 const source=evidenceSourceUrl('data:application/json;base64,abc',warehouse,{createObjectURL:blob=>{created=blob;return 'blob:test-source'},revokeObjectURL:url=>released.push(url)});
 assert.equal(source.url,'blob:test-source');assert.equal(JSON.parse(await created!.text()).engine_bytes,52_792_260);
 source.release();source.release();assert.deepEqual(released,['blob:test-source']);
 const asset=evidenceSourceUrl('/assets/source-report.json',warehouse,{createObjectURL:()=>{throw new Error('must not allocate')},revokeObjectURL:()=>{throw new Error('must not revoke')}});
 assert.equal(asset.url,'/assets/source-report.json');asset.release();
});
