import { useCallback, useEffect, useRef, useState } from 'react';
import { Play, Pause, RotateCcw, Film, AlertTriangle } from 'lucide-react';
import { pointInPolygon } from './domain';
import { nearestMetadataFrame, validMetadataTimeline } from './replaySync';

type Detection = { bbox: number[]; track_id: string|null; class_name: string; confidence: number };
type TimelineFrame = { frame_index: number; pts_ns: number; camera_id: string; frame_width:number; frame_height:number; detections: Detection[] };
type Timeline = { video_url: string|null; video_available: boolean; frame_width:number; frame_height:number; camera_id:string; pts_offset_ns:number|null; timestamp_mapping_configured:boolean; tolerance_ns:number; metadata_sha256:string; frames: TimelineFrame[] };
type Zone = {id:string;name:string;camera_id:string;polygon:number[][];confidence_threshold:number};
type Props = {zones:Zone[];socketUp:boolean;large:boolean;fallback:React.ReactNode};
const stamp=(seconds:number)=>`${Math.floor(seconds/60)}:${(seconds%60).toFixed(2).padStart(5,'0')}`;
let timelineRequest:Promise<Timeline>|null=null;
function loadTimeline(){
 if(!timelineRequest)timelineRequest=fetch('/api/replay/timeline').then(async res=>{if(!res.ok)throw new Error(`Timeline unavailable (${res.status})`);return res.json() as Promise<Timeline>}).then(value=>{if(!validMetadataTimeline(value.frames))throw new Error('Metadata timeline has invalid or unsorted PTS; overlays disabled.');return value}).catch(error=>{timelineRequest=null;throw error});
 return timelineRequest;
}
export default function RecordedVideoViewer({zones,socketUp,large,fallback}:Props){
 const [timeline,setTimeline]=useState<Timeline|null>(null),[error,setError]=useState(''),[videoFailed,setVideoFailed]=useState(false),[time,setTime]=useState(0),[duration,setDuration]=useState(0),[paused,setPaused]=useState(true),[speed,setSpeed]=useState('1'),[matched,setMatched]=useState<TimelineFrame|null>(null),[seeking,setSeeking]=useState(false),[mismatch,setMismatch]=useState(false);
 const video=useRef<HTMLVideoElement>(null);const timeRef=useRef(0);const seekPending=useRef(false);
 const reload=useCallback(()=>{setError('');setVideoFailed(false);timelineRequest=null;void loadTimeline().then(setTimeline).catch(err=>setError((err as Error).message))},[]);
 useEffect(()=>{let disposed=false;void loadTimeline().then(value=>{if(!disposed)setTimeline(value)}).catch(err=>{if(!disposed)setError((err as Error).message)});return()=>{disposed=true}},[]);
 const synchronize=useCallback((mediaTime:number)=>{
  if(!timeline||!Number.isFinite(mediaTime))return;
  timeRef.current=mediaTime;setTime(mediaTime);
  const next=nearestMetadataFrame(timeline.frames,mediaTime,{toleranceNs:timeline.tolerance_ns,ptsOffsetNs:timeline.pts_offset_ns});
  setMatched(previous=>previous?.frame_index===next?.frame_index?previous:next);
 },[timeline]);
 useEffect(()=>{
  const element=video.current;if(!element||!timeline||!timeline.video_available||videoFailed)return;
  let stopped=false,videoCallback=0,animation=0;
  const tick=(_now:number,metadata:VideoFrameCallbackMetadata)=>{if(stopped)return;seekPending.current=false;setSeeking(false);synchronize(metadata.mediaTime);videoCallback=element.requestVideoFrameCallback(tick)};
  const fallbackTick=()=>{if(stopped)return;if(!element.seeking)synchronize(element.currentTime);animation=requestAnimationFrame(fallbackTick)};
  if(typeof element.requestVideoFrameCallback==='function')videoCallback=element.requestVideoFrameCallback(tick);else animation=requestAnimationFrame(fallbackTick);
  return()=>{stopped=true;if(videoCallback&&element.cancelVideoFrameCallback)element.cancelVideoFrameCallback(videoCallback);cancelAnimationFrame(animation)};
 },[timeline,synchronize,videoFailed]);
 const available=timeline?.video_available&&timeline.video_url&&!videoFailed;
 const relevantZones=zones.filter(zone=>zone.camera_id===(matched?.camera_id??timeline?.camera_id));
 const inside=(detection:Detection)=>detection.class_name==='person'&&relevantZones.some(zone=>detection.confidence>=zone.confidence_threshold&&pointInPolygon([(detection.bbox[0]+detection.bbox[2])/2,detection.bbox[3]],zone.polygon));
 const detections=!seeking&&!mismatch?matched?.detections??[]:[];
 const occupancy=detections.filter(inside).length;
 const seek=(value:number)=>{if(video.current){seekPending.current=true;setSeeking(true);setMatched(null);setTime(value);video.current.currentTime=value}};
 const toggle=()=>{const element=video.current;if(!element)return;if(element.paused)void element.play().catch(err=>setError(`Video playback failed: ${(err as Error).message}`));else element.pause()};
 if(!timeline&&!error)return <section className="panel recorded-loading"><Film size={24}/><h2>Loading recorded video timeline…</h2><p>Reading genuine PipeGen metadata. No detection boxes are synthesized.</p></section>;
 if(!available)return <><div className="recorded-fallback"><AlertTriangle size={18}/><span>{error||'Original recorded video is unavailable. Showing metadata only.'}</span><button className="text-button" onClick={reload}>Retry video</button></div>{fallback}</>;
 const width=timeline!.frame_width,height=timeline!.frame_height;
 return <section className={`panel recorded-viewer ${large?'large':''}`} aria-label="Synchronized recorded PipeGen video viewer">
  <div className="panel-heading"><div><span className="eyebrow">REAL PIPEGEN REPLAY · RECORDED VIDEO</span><h2>People crossing · Safety monitoring</h2></div><div className="monitor-status"><span className="badge blue">YOLOv8m / TensorRT FP16</span>{occupancy>0&&<span className="badge critical">{occupancy} INSIDE ZONE</span>}</div></div>
  <div className="recorded-stage" style={{aspectRatio:`${width}/${height}`}}>
   <video ref={video} src={timeline!.video_url!} preload="auto" muted playsInline onLoadedMetadata={e=>{const element=e.currentTarget;setDuration(element.duration);setMismatch(element.videoWidth!==width||element.videoHeight!==height);synchronize(element.currentTime)}} onPlay={()=>setPaused(false)} onPause={()=>setPaused(true)} onEnded={()=>{setPaused(true);if(video.current&&typeof video.current.requestVideoFrameCallback!=='function')synchronize(video.current.currentTime)}} onSeeking={()=>{seekPending.current=true;setSeeking(true);setMatched(null)}} onSeeked={e=>{if(typeof e.currentTarget.requestVideoFrameCallback!=='function'){seekPending.current=false;setSeeking(false);synchronize(e.currentTarget.currentTime)}else if(!seekPending.current)setSeeking(false)}} onTimeUpdate={e=>{if(typeof e.currentTarget.requestVideoFrameCallback!=='function'&&!e.currentTarget.seeking)synchronize(e.currentTarget.currentTime)}} onError={()=>{setVideoFailed(true);setError('The recorded MP4 could not be played. Metadata-only fallback is active.')}} aria-label="Original recorded people-crossing video"/>
   <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet" aria-label="Synchronized real person detection and restricted zone overlay">
    {!mismatch&&relevantZones.map(zone=><g key={zone.id}><polygon className="recorded-zone" points={zone.polygon.map(p=>`${p[0]*width},${p[1]*height}`).join(' ')}/><text className="recorded-zone-label" x={zone.polygon[0][0]*width+10} y={zone.polygon[0][1]*height+31}>{zone.name}</text></g>)}
    {detections.map((d,index)=>{const [x1,y1,x2,y2]=d.bbox;const alert=inside(d);const caption=`ID ${d.track_id??'untracked'} · ${Math.round(d.confidence*100)}%${alert?' · INSIDE':''}`;const labelY=Math.max(0,y1*height-32);return <g key={`${d.track_id}-${index}`} className={alert?'recorded-person inside':'recorded-person'}><rect className="person-box" x={x1*width} y={y1*height} width={(x2-x1)*width} height={(y2-y1)*height}/><rect className="person-caption-bg" x={x1*width} y={labelY} width={Math.min(width-x1*width,caption.length*13+16)} height="30" rx="3"/><text className="person-caption" x={x1*width+8} y={labelY+22}>{caption}</text><circle cx={(x1+x2)/2*width} cy={y2*height} r="5" className="foot-point"/></g>})}
   </svg>
   <div className="recorded-top"><span>{timeline!.camera_id} · RECORDED</span><span>{paused?'PAUSED':'PLAYING'} · {speed}×</span></div>
   <div className="recorded-frame-info" data-media-time={time.toFixed(9)} data-frame-index={matched?.frame_index??'unmatched'} data-pts-ns={matched?.pts_ns??''} data-offset-ns={timeline!.pts_offset_ns??'unverified'} data-delta-ns={matched&&timeline!.pts_offset_ns!=null?Math.round(matched.pts_ns-(time*1e9+timeline!.pts_offset_ns)):''}><span>{seeking?'Seeking · overlays withheld':mismatch?'Source dimensions mismatch · boxes withheld':timeline!.pts_offset_ns==null?'Timestamp mapping not verified · boxes withheld':matched?`Frame ${matched.frame_index} · PTS ${(matched.pts_ns/1e9).toFixed(6)} s`:'No metadata within tolerance · no boxes shown'}</span><span>media {time.toFixed(6)} s · Δ {matched&&timeline!.pts_offset_ns!=null?((matched.pts_ns-(time*1e9+timeline!.pts_offset_ns))/1e6).toFixed(3)+' ms':'unmatched'}</span></div>
   {paused&&time===0&&<button className="recorded-play-overlay" onClick={toggle} aria-label="Play recorded video"><Play size={32}/></button>}
  </div>
  <div className="video-controls"><button className="icon-button" onClick={toggle} aria-label={paused?'Play recorded video':'Pause recorded video'}>{paused?<Play size={19}/>:<Pause size={19}/>}</button><button className="icon-button" onClick={()=>seek(0)} aria-label="Seek to beginning"><RotateCcw size={16}/></button><span className="video-time">{stamp(time)} / {stamp(duration)}</span><input type="range" min="0" max={duration||1} step="0.001" value={Math.min(time,duration||1)} onChange={e=>seek(Number(e.target.value))} aria-label="Recorded video seek"/><label className="video-speed"><span>Playback speed</span><select aria-label="Video playback speed" value={speed} onChange={e=>{setSpeed(e.target.value);if(video.current)video.current.playbackRate=Number(e.target.value)}}>{[.25,.5,1,1.5,2,4].map(value=><option key={value} value={value}>{value}×</option>)}</select></label></div>
  <div className="recorded-footer"><span><i className={'status-dot '+(socketUp?'green':'amber')}/>{socketUp?'Backend updates connected':'Backend reconnecting'}</span><span>{width} × {height} · Original video + real metadata · No live inference</span></div>
  <p className="recorded-note">Playback and seeking do not create incidents. Red boxes use the current polygon and person foot position; changing a zone changes application analysis, never the original PipeGen detections.</p>
  {error&&<p className="recorded-warning" role="alert">{error}</p>}
  {mismatch&&<p className="recorded-warning" role="alert">Video dimensions do not match metadata. Detection overlays are disabled.</p>}
 </section>;
}
