export type FrameIdentity={session_id:string;seq:number;media_time:number};
/** Only one captured frame is admitted; a returned frame must match all capture identity fields. */
export class FrameFlightGate {
 private generation=0;private pending:({generation:number}&FrameIdentity)|null=null;
 begin(frame:FrameIdentity){if(this.pending)return null;return this.pending={...frame,generation:this.generation}}
 accepts(token:{generation:number}&FrameIdentity,response:FrameIdentity){return this.pending===token&&token.generation===this.generation&&response.session_id===token.session_id&&response.seq===token.seq&&Number.isFinite(response.media_time)&&Math.abs(response.media_time-token.media_time)<1e-6}
 finish(token:unknown){if(this.pending===token)this.pending=null}
 reset(){this.generation++;this.pending=null}
}
export function cameraFailure(error:unknown):string {
 const name=(error as {name?:string})?.name;
 if(name==='NotAllowedError'||name==='SecurityError')return 'Camera permission denied. Allow camera access in your browser and connect again.';
 if(name==='NotFoundError'||name==='DevicesNotFoundError')return 'No camera is available. Connect a working USB camera or choose another source.';
 if(name==='NotReadableError'||name==='TrackStartError')return 'Camera cannot be read. It may be disconnected or in use by another application.';
 return error instanceof Error?error.message:'Camera connection failed.';
}
export function releaseCamera(stream:{getTracks:()=>{stop:()=>void;onended?:unknown}[]}|null){for(const track of stream?.getTracks()??[]){track.onended=null;track.stop()}}
export function validateVideoFile(file:{name:string;type:string;size:number}):string|null {
 if(!file.name.toLowerCase().endsWith('.mp4')||!['video/mp4',''].includes(file.type))return 'Select an MP4 video. Other formats are not supported.';
 if(file.size<=0)return 'The selected video is empty.';
 if(file.size>250*1024*1024)return 'Select an MP4 smaller than 250 MiB. The file stays in your browser.';
 return null;
}
/** Being first observed inside is not proof of crossing a boundary. */
export function aiIncidentLabel(eventType:string,entryBasis?:string):string {
 if(entryBasis==='first_observed_inside')return 'First observed inside';
 if(entryBasis==='observed_outside_to_inside')return 'Observed zone entry';
 return eventType.replace(/_/g,' ');
}
