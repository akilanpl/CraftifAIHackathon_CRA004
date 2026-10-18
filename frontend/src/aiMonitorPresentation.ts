/** Display state only: never derives detector results or changes capture/session logic. */
export type MonitorSource='simulation'|'virtual_video'|'uploaded_video'|'usb_camera';
export type MonitorHealth={id:string;label:string;value:string;tone:'good'|'warning'|'neutral';detail:string};
export function sourceCardIndex(key:string,current:number,count:number):number|null {
 if(key==='ArrowRight'||key==='ArrowDown')return (current+1)%count;
 if(key==='ArrowLeft'||key==='ArrowUp')return (current+count-1)%count;
 if(key==='Home')return 0;if(key==='End')return count-1;return null;
}
export function monitorHealth(input:{primaryBackendConnected?:boolean;primarySocketConnected?:boolean;checking:boolean;checked:boolean;serviceOnline:boolean;inferenceAvailable:boolean;serviceUncertain:boolean;source:MonitorSource;cameraConnected:boolean;hasVideo:boolean;videoLoaded:boolean;sourceFailed:boolean;simulationAvailable:boolean;sessionState?:string;running:boolean;complete:boolean}):MonitorHealth[]{
 const primary:MonitorHealth={id:'primary',label:'Warehouse V2 API',value:input.primaryBackendConnected===undefined?'Not checked':input.primaryBackendConnected?'Connected':'Disconnected',tone:input.primaryBackendConnected?'good':input.primaryBackendConnected===false?'warning':'neutral',detail:input.primarySocketConnected===undefined?'Primary service health only':input.primarySocketConnected?'Primary updates connected':'Primary updates disconnected'};
 const service:MonitorHealth={id:'independent',label:'Independent AI service',value:input.checking?'Checking…':input.serviceUncertain?'Recheck required':!input.checked?'Not checked':!input.serviceOnline?'Unavailable':input.inferenceAvailable?'Inference ready':'Inference unavailable',tone:input.checking||!input.checked?'neutral':input.serviceUncertain||!input.serviceOnline||!input.inferenceAvailable?'warning':'good',detail:'Separate from the Warehouse V2 backend'};
 const source:MonitorHealth={id:'source',label:'Selected source',value:'',tone:'neutral',detail:'No inference is implied by source readiness'};
 if(input.source==='simulation'){source.value=input.simulationAvailable?'Fixture ready':'Service required';source.tone=input.simulationAvailable?'warning':'neutral';source.detail='Simulated business-logic fixtures · not model output'}
 else if(input.source==='usb_camera'){source.value=input.cameraConnected?'Camera connected':'Camera not connected';source.tone=input.cameraConnected?'good':'neutral';source.detail='Hardware acceptance remains NOT TESTED'}
 else if(input.sourceFailed){source.value='Video unavailable';source.tone='warning'}
 else if(!input.hasVideo)source.value='Select an MP4';
 else {source.value=input.videoLoaded?'Video loaded':'Loading video';source.tone=input.videoLoaded?'good':'neutral'}
 const session:MonitorHealth={id:'session',label:'Monitoring session',value:input.complete?'Complete':input.running?'Sampling frames':input.sessionState==='running'?(input.source==='simulation'?'Fixture session ready':'Ready · not sampling'):input.sessionState??'Idle',tone:input.running?'good':'neutral',detail:'Session state is independent of service availability'};
 return [primary,service,source,session];
}
