/** Presentation helpers only. No benchmark is inferred from playback or another report. */
export type EvidenceMetric={label:string;value:string;unit?:string;scope:string};
export function evidenceNumber(value:unknown,digits=0):string {
 return typeof value==='number'&&Number.isFinite(value)?value.toLocaleString('en-US',{minimumFractionDigits:digits,maximumFractionDigits:digits}):'Not reported';
}
export function measuredRange(values:unknown[],digits=2):string {
 const numbers=values.filter((value):value is number=>typeof value==='number'&&Number.isFinite(value));
 if(!numbers.length)return 'Not reported';
 const minimum=Math.min(...numbers),maximum=Math.max(...numbers);
 return minimum===maximum?evidenceNumber(minimum,digits):`${evidenceNumber(minimum,digits)}–${evidenceNumber(maximum,digits)}`;
}
export function warehouseMetrics(report:{measured_gpu_compute_ms:unknown;measured_end_to_end_engine_ms:unknown;reported_engine_throughput_qps:unknown;reported_power:{engine_power_w:unknown;power_accuracy_w:unknown}}):EvidenceMetric[]{
 return [
  {label:'GPU compute',value:evidenceNumber(report.measured_gpu_compute_ms,5),unit:'ms',scope:'Reported engine benchmark'},
  {label:'End-to-end engine',value:evidenceNumber(report.measured_end_to_end_engine_ms,5),unit:'ms',scope:'Engine scope · excludes full pipeline'},
  {label:'Engine throughput',value:evidenceNumber(report.reported_engine_throughput_qps,3),unit:'inferences/s',scope:'Reported throughput · not video FPS'},
  {label:'GPU-board power',value:evidenceNumber(report.reported_power.engine_power_w,3),unit:'W',scope:`Engine run · reported accuracy ±${evidenceNumber(report.reported_power.power_accuracy_w)} W`},
 ];
}
export function accuracyReviewState(report:{formal_metrics_available?:boolean;image_count?:number;human_reviewed_image_count?:number}){
 const complete=report.formal_metrics_available===true&&typeof report.image_count==='number'&&report.image_count>0&&report.image_count===report.human_reviewed_image_count;
 return {complete,label:complete?'REVIEWED DATASET REPORT':'PENDING HUMAN REVIEW',reviewed:report.human_reviewed_image_count??0,total:report.image_count??0};
}
export async function copyEvidenceJson(value:unknown,clipboard?:{writeText:(text:string)=>Promise<void>}):Promise<void>{
 if(!clipboard)throw new Error('Clipboard access is unavailable. Open the source JSON to copy it manually.');
 const text=JSON.stringify(value,null,2);
 if(typeof text!=='string')throw new Error('The source could not be serialized as JSON.');
 await clipboard.writeText(text);
}
/** Small Vite assets can be data URLs, which browsers block in new tabs. */
export function evidenceSourceUrl(assetUrl:string,data:unknown,urls:{createObjectURL:(blob:Blob)=>string;revokeObjectURL:(url:string)=>void}=URL){
 if(!assetUrl.startsWith('data:'))return {url:assetUrl,release:()=>{}};
 const text=JSON.stringify(data,null,2);
 if(typeof text!=='string')throw new Error('The source could not be serialized as JSON.');
 const url=urls.createObjectURL(new Blob([text],{type:'application/json'}));let released=false;
 return {url,release:()=>{if(!released){released=true;urls.revokeObjectURL(url)}}};
}
