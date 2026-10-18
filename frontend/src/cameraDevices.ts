/** App-owned camera seam. The harness never replaces navigator.mediaDevices. */
export type CameraDevice={deviceId:string;label:string;kind:MediaDeviceKind};
export type CameraDeviceAccess={getUserMedia(constraints:MediaStreamConstraints):Promise<MediaStream>;enumerateDevices():Promise<CameraDevice[]>;release?(stream:MediaStream):void;dispose?():void};
export type CameraHarnessMode='connected'|'permission_denied'|'unavailable';
export type CaptureResource={stream:MediaStream;release:()=>void};
export function cameraHarnessEnabled(context:{hostname:string;search:string;dev:boolean}):boolean {
 return context.dev&&['localhost','127.0.0.1','::1','[::1]'].includes(context.hostname)&&new URLSearchParams(context.search).get('cameraTest')==='1';
}
export function browserCameraDevices():CameraDeviceAccess {
 return {getUserMedia:constraints=>{if(!navigator.mediaDevices?.getUserMedia)return Promise.reject(new Error('Camera access requires localhost or HTTPS and a supported browser.'));return navigator.mediaDevices.getUserMedia(constraints)},enumerateDevices:async()=>navigator.mediaDevices?.enumerateDevices?await navigator.mediaDevices.enumerateDevices():[]};
}
/** Real video pixels become a browser MediaStream; no metadata is read. */
export async function captureRecordedCamera(url:string,signal?:AbortSignal):Promise<CaptureResource> {
 const video=document.createElement('video');video.src=url;video.muted=true;video.playsInline=true;video.loop=true;video.preload='auto';video.hidden=true;video.setAttribute('aria-hidden','true');document.body.appendChild(video);
 const disposeVideo=()=>{video.pause();video.removeAttribute('src');video.load();video.remove()};const cancel=()=>disposeVideo();signal?.addEventListener('abort',cancel,{once:true});
 try{
  await new Promise<void>((resolve,reject)=>{const cleanup=()=>{clearTimeout(timeout);video.removeEventListener('loadeddata',ready);video.removeEventListener('error',failed);signal?.removeEventListener('abort',aborted)};const aborted=()=>{cleanup();reject(new DOMException('Simulated camera request canceled','AbortError'))};const ready=()=>{cleanup();resolve()};const failed=()=>{cleanup();reject(new Error('Simulated USB source video could not be decoded.'))};const timeout=window.setTimeout(()=>{cleanup();reject(new Error('Simulated USB source video timed out.'))},15000);video.addEventListener('loadeddata',ready,{once:true});video.addEventListener('error',failed,{once:true});signal?.addEventListener('abort',aborted,{once:true});if(signal?.aborted){aborted();return}video.load()});
  await video.play();if(signal?.aborted)throw new DOMException('Simulated camera request canceled','AbortError');
  const supported=video as HTMLVideoElement&{captureStream?:()=>MediaStream;mozCaptureStream?:()=>MediaStream};
  const capture=supported.captureStream??supported.mozCaptureStream;if(!capture)throw new Error('This browser does not support video.captureStream(). Physical camera access was not attempted.');
  const stream=capture.call(video);for(const track of stream.getAudioTracks()){track.stop();stream.removeTrack(track)}if(!stream.getVideoTracks().length)throw new Error('Recorded-video capture produced no video track.');
  return {stream,release:()=>{signal?.removeEventListener('abort',cancel);for(const track of stream.getTracks())track.stop();disposeVideo()}};
 }catch(error){signal?.removeEventListener('abort',cancel);disposeVideo();throw error}
}
export class SimulatedUsbDevices implements CameraDeviceAccess {
 private capture:(deviceId:string,signal:AbortSignal)=>Promise<CaptureResource>;private pending=new Set<AbortController>();private notify:()=>void;private resources=new Map<MediaStream,CaptureResource>();private generation=0;
 mode:CameraHarnessMode='connected';requests=0;opened=0;released=0;lastDevice='';
 constructor(capture:(deviceId:string,signal:AbortSignal)=>Promise<CaptureResource>,notify:()=>void=()=>{}){this.capture=capture;this.notify=notify}
 snapshot(){return {mode:this.mode,requests:this.requests,opened:this.opened,released:this.released,activeStreams:this.resources.size,liveTracks:[...this.resources.keys()].flatMap(stream=>stream.getTracks()).filter(track=>track.readyState==='live').length,lastDevice:this.lastDevice}}
 async enumerateDevices():Promise<CameraDevice[]>{return this.mode==='unavailable'?[]:[{deviceId:'sim-usb-a',kind:'videoinput',label:'SIMULATED USB · Warehouse capture A'},{deviceId:'sim-usb-b',kind:'videoinput',label:'SIMULATED USB · Warehouse capture B'}]}
 async getUserMedia(constraints:MediaStreamConstraints):Promise<MediaStream>{
  this.requests++;this.notify();if(this.mode==='permission_denied')throw new DOMException('App-owned simulated permission denial','NotAllowedError');if(this.mode==='unavailable')throw new DOMException('App-owned simulated missing device','NotFoundError');
  const video=constraints.video;const selected=typeof video==='object'&&typeof video.deviceId==='object'&&'exact' in video.deviceId?video.deviceId.exact:'sim-usb-a';const device=Array.isArray(selected)?selected[0]:selected||'sim-usb-a';
  if(!['sim-usb-a','sim-usb-b'].includes(device))throw new DOMException('Simulated device not found','NotFoundError');
  const generation=this.generation;const controller=new AbortController();this.pending.add(controller);let resource:CaptureResource;try{resource=await this.capture(device,controller.signal)}finally{this.pending.delete(controller)}
  if(generation!==this.generation||this.mode!=='connected'){resource.release();this.released++;this.notify();throw new DOMException('Camera request canceled','AbortError')}
  this.resources.set(resource.stream,resource);this.opened++;this.lastDevice=device;this.notify();return resource.stream;
 }
 release(stream:MediaStream){const resource=this.resources.get(stream);if(!resource)return;this.resources.delete(stream);resource.release();this.released++;this.notify()}
 private cancelPending(){for(const controller of this.pending)controller.abort();this.pending.clear()}
 setMode(mode:CameraHarnessMode){this.mode=mode;this.generation++;this.cancelPending();if(mode!=='connected')this.disconnectStreams();this.notify()}
 disconnect(){this.mode='unavailable';this.generation++;this.cancelPending();this.disconnectStreams();this.notify()}
 private disconnectStreams(){for(const stream of [...this.resources.keys()]){const tracks=stream.getVideoTracks();this.release(stream);for(const track of tracks)track.dispatchEvent(new Event('ended'))}}
 dispose(){this.generation++;this.cancelPending();for(const stream of [...this.resources.keys()])this.release(stream)}
}
