import {useEffect,useState} from 'react';
import {Copy,Check,FileText,ExternalLink,Info} from 'lucide-react';
import historical from '../../evidence/04-tensorrt-fp16/measured-engine-summary.json';
import warehouse from '../../evidence/04-tensorrt-fp16/warehouse-engine-summary.json';
import cpu from '../../evidence/independent-ai/cpu-runtime-validation.json';
import exportAudit from '../../evidence/factory-export-audit.json';
import evaluation from '../../evidence/evaluation/independent-detection-evaluation.json';
import warehouseUrl from '../../evidence/04-tensorrt-fp16/warehouse-engine-summary.json?url';
import historicalUrl from '../../evidence/04-tensorrt-fp16/measured-engine-summary.json?url';
import cpuUrl from '../../evidence/independent-ai/cpu-runtime-validation.json?url';
import evaluationUrl from '../../evidence/evaluation/independent-detection-evaluation.json?url';
import {accuracyReviewState,copyEvidenceJson,evidenceSourceUrl,evidenceNumber,measuredRange,warehouseMetrics,type EvidenceMetric} from './modelEvidence';
import './modelPerformance.css';

function SourceFile({path,url,data,label}:{path:string;url:string;data:unknown;label:string}){
 const [message,setMessage]=useState(''),[copied,setCopied]=useState(false),[failed,setFailed]=useState(false),[sourceUrl,setSourceUrl]=useState(url.startsWith('data:')?'':url);
 useEffect(()=>{try{const source=evidenceSourceUrl(url,data);setSourceUrl(source.url);return source.release}catch(error){setFailed(true);setMessage(`Source unavailable: ${error instanceof Error?error.message:'Open the repository JSON manually.'}`)}},[url,data]);
 const copy=async()=>{setMessage('');setFailed(false);setCopied(false);try{await copyEvidenceJson(data,navigator.clipboard);setCopied(true);setMessage(`${label} source JSON copied.`)}catch(error){setFailed(true);setMessage(`Copy failed: ${error instanceof Error?error.message:'Clipboard permission was denied.'}`)}};
 return <div className="me-source-group"><div className="me-source"><span>Source JSON file</span><a href={sourceUrl||undefined} aria-disabled={!sourceUrl} target="_blank" rel="noreferrer" aria-label={`Open ${label} source JSON in a new tab`}>{path}<ExternalLink size={12}/></a><button type="button" onClick={()=>void copy()} aria-label={`Copy ${label} source JSON`} title="Copy source JSON">{copied?<Check size={16}/>:<Copy size={16}/>}</button></div>{message&&<p className={failed?'me-copy-message failed':'me-copy-message'} role={failed?'alert':'status'}>{message}</p>}</div>;
}
function Metrics({items}:{items:EvidenceMetric[]}){
 return <div className="me-metrics">{items.map(metric=><article className="me-metric" key={metric.label}><span>{metric.label}</span><strong>{metric.value}{metric.unit&&<small>{metric.unit}</small>}</strong><p>{metric.scope}</p></article>)}</div>;
}
export default function ModelPerformance(){
 const review=accuracyReviewState(evaluation);
 const power=warehouse.reported_power;
 const warehouseDetails=[
  ['Model / precision',`${warehouse.model} / ${warehouse.precision.toUpperCase()}`],
  ['TensorRT / layers',`${warehouse.tensorrt} / ${warehouse.layer_count}`],
  ['Input tensor',warehouse.input_shape.join(' × ')],
  ['Layer precision',`${warehouse.precision_mix.FP16} FP16 · ${warehouse.precision_mix.FP32} FP32`],
  ['Benchmark device',warehouse.benchmark_device_in_report],
  ['Engine size',`${evidenceNumber(warehouse.engine_bytes)} bytes`],
  ['Build duration',`${warehouse.build_seconds} s · new build, not cache`],
  ['Compilation / export',warehouse.built && exportAudit.engine_expected_hash_matches && exportAudit.engine_sha256===warehouse.engine_sha256?'Compiled · exported engine hash verified':'Verification unavailable'],
  ['Power source / sampling',`${power.power_source} · ${power.power_samples} samples · ${power.power_sample_basis.replace(/_/g,' ')}`],
  ['Power scope / reported accuracy',`GPU board · engine run · ±${evidenceNumber(power.power_accuracy_w)} W`],
  ['Power verification','Reported by PipeGen; not independently remeasured by this audit'],
  ['Semantic model version',warehouse.semantic_model_version],
  ['Engine SHA-256',warehouse.engine_sha256],
 ];
 const untested=[
  ['Full-pipeline performance','NOT MEASURED','Engine timings exclude the complete decode, tracking, analytics, storage, and application path.'],
  ['Whole-system / full-pipeline power','NOT TESTED','Reported GPU-board engine-run power does not measure whole-system or full-pipeline consumption.'],
  ['INT8 comparison','NOT TESTED','No measured INT8 engine, power, or accuracy comparison is supplied. FP16 alone establishes no accuracy advantage.'],
  ['Precision / recall / mAP',review.label,'Formal accuracy remains gated until all evaluation frames have approved human ground truth. Predictions are never ground truth.'],
  ['Jetson deployment','NOT TESTED','Orin NX values in the historical report are modeled estimates, not results from a deployed Jetson.'],
  ['Physical USB camera','NOT TESTED','Recorded-video and simulated-USB tests do not establish physical camera acceptance.'],
 ];
 return <div className="model-evidence">
  <section className="me-panel" aria-labelledby="warehouse-engine-title"><div className="me-heading"><div><span className="me-eyebrow">WAREHOUSE FP16 V2 · ENGINE EVIDENCE</span><h2 id="warehouse-engine-title">Compiled model benchmark</h2></div><span className="me-status reported">RECORDED REPORT</span></div><p className="me-intro">Reported TensorRT engine results for the warehouse build. Engine timing, independent CPU processing, and complete pipeline performance are separate scopes.</p>
   <Metrics items={warehouseMetrics(warehouse)}/>
   <div className="me-details" role="region" tabIndex={0} aria-label="Warehouse engine details"><table><caption>Warehouse compiled engine details</caption><tbody>{warehouseDetails.map(([label,value])=><tr key={label}><th scope="row">{label}</th><td className={label==='Engine SHA-256'?'me-hash':''}>{value}</td></tr>)}</tbody></table></div>
   <div className="me-caveat"><Info size={15}/><p>Throughput is the report’s engine benchmark value, not camera FPS or a reciprocal derived from either latency above. {warehouse.caveat} <a href="https://github.com/akilanpl/hazard-zone-sentinel/blob/main/evidence/factory-export-audit.json" target="_blank" rel="noreferrer">Export audit</a></p></div>
   <SourceFile path="evidence/04-tensorrt-fp16/warehouse-engine-summary.json" url={warehouseUrl} data={warehouse} label="Warehouse engine"/>
  </section>
  <section className="me-historical" aria-labelledby="historical-engine-title"><div className="me-notice"><FileText size={24}/><div><h2 id="historical-engine-title">Historical engine evidence</h2><p>Separate earlier model benchmark. These measurements are not assigned to the warehouse build or the independent CPU service.</p></div><span className="me-status">HISTORICAL REPORT</span></div><Metrics items={[
   {label:'GPU compute time',value:evidenceNumber(historical.measured_gpu_compute_ms,5),unit:'ms',scope:'Earlier engine benchmark'},
   {label:'End-to-end engine time',value:evidenceNumber(historical.measured_end_to_end_engine_ms,5),unit:'ms',scope:'Engine scope · not full pipeline'},
   {label:'Engine precision',value:historical.precision.toUpperCase(),scope:`${historical.layer_count} layers · ${evidenceNumber(historical.engine_bytes)} bytes`},
  ]}/><p className="me-section-note">Benchmark device: {historical.benchmark_device_in_report}. {historical.caveat}</p><SourceFile path="evidence/04-tensorrt-fp16/measured-engine-summary.json" url={historicalUrl} data={historical} label="Historical engine"/></section>
  <section className="me-panel" aria-labelledby="cpu-validation-title"><div className="me-heading"><div><span className="me-eyebrow">INDEPENDENT AI · CPU VALIDATION SAMPLE</span><h2 id="cpu-validation-title">Recorded-frame CPU processing</h2></div><span className="me-status">{cpu.model.engine} · {cpu.model.runtime_version}</span></div><p className="me-intro">{cpu.frames.length} genuine recorded-video frames processed by the independent ONNX Runtime CPU worker. This stored sample is not current service telemetry or an NVIDIA engine benchmark.</p><Metrics items={[
   {label:'Processing latency range',value:measuredRange(cpu.frames.map(frame=>frame.processing_latency_ms)),unit:'ms',scope:`${cpu.frames.length}-frame CPU process sample`},
   {label:'Reported processing rate',value:measuredRange(cpu.frames.map(frame=>frame.processing_fps)),unit:'frames/s',scope:'Per-frame worker reports · not full-pipeline FPS'},
   {label:'Execution provider',value:'CPU',scope:cpu.model.providers.join(', ')},
  ]}/><p className="me-section-note">{cpu.source}. Model: {cpu.model.model}. Inference confidence threshold: {cpu.confidence_threshold}. Physical camera hardware: {cpu.physical_camera_hardware_test}.</p><SourceFile path="evidence/independent-ai/cpu-runtime-validation.json" url={cpuUrl} data={cpu} label="Independent CPU validation"/></section>
  <section className="me-panel" aria-labelledby="evidence-boundaries-title"><div className="me-heading"><div><span className="me-eyebrow">MEASUREMENT BOUNDARIES</span><h2 id="evidence-boundaries-title">What the evidence does not establish</h2></div><span className="me-status pending">NO INFERRED RESULTS</span></div><div className="me-boundary-table" role="region" tabIndex={0} aria-label="Untested measurements"><table><caption>Measurement scope and remaining validation</caption><thead><tr><th scope="col">Metric / target</th><th scope="col">Status</th><th scope="col">Evidence boundary</th></tr></thead><tbody>{untested.map(([name,status,explanation])=><tr key={name}><th scope="row">{name}</th><td><span className="me-status pending">{status}</span></td><td>{explanation}</td></tr>)}</tbody></table></div></section>
  <section className="me-panel" aria-labelledby="accuracy-review-title"><div className="me-heading"><div><span className="me-eyebrow">FORMAL ACCURACY · SEPARATE REVIEW WORKFLOW</span><h2 id="accuracy-review-title">Human annotation review</h2></div><span className="me-status pending">{review.label}</span></div><p className="me-intro">The review package contains {review.total} frames. Partial annotation exports do not establish completed evaluation. Precision, recall, and AP remain withheld until the complete ground-truth set is approved.</p><p className="me-review-note">The release audit and formal evaluation are separate snapshots. Partial review is not a measured accuracy result.</p><SourceFile path="evidence/evaluation/independent-detection-evaluation.json" url={evaluationUrl} data={evaluation} label="Formal evaluation"/></section>
 </div>;
}
