"""Read-only, explicitly configured recorded video and metadata timeline.

Playback never runs the intrusion engine or writes incident state.
"""
import hashlib
import os
from pathlib import Path
import re
from fastapi import HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from .replay import load_export


class ReplayVideo:
    def __init__(self,path=None,offset_ns=None,tolerance_ns=None,use_env=True):
        configured=path or (os.getenv('SENTINEL_REPLAY_VIDEO') if use_env else None)
        self.path=Path(configured).resolve() if configured else None
        self.offset_ns=self._integer_setting(offset_ns if offset_ns is not None else (os.getenv('SENTINEL_REPLAY_VIDEO_PTS_OFFSET_NS') if use_env else None),None,'PTS offset')
        self.tolerance_ns=self._integer_setting(tolerance_ns if tolerance_ns is not None else (os.getenv('SENTINEL_REPLAY_VIDEO_TOLERANCE_NS') if use_env else None),8350000,'timestamp tolerance')
        if self.tolerance_ns<0 or self.tolerance_ns>1000000000:
            raise ValueError('Replay timestamp tolerance must be between zero and one second')

    @staticmethod
    def _integer_setting(value,default,label):
        if value is None:
            return default
        if isinstance(value,bool) or not re.fullmatch(r'-?\d+',str(value)):
            raise ValueError('Replay '+label+' must be an explicit integer in nanoseconds')
        return int(value)

    def checked_path(self):
        if self.path is None:
            raise HTTPException(404,'Replay video is not configured')
        try:
            if self.path.suffix.lower()!='.mp4' or not self.path.is_file() or not os.access(self.path,os.R_OK):
                raise ValueError('Unavailable video')
            with self.path.open('rb') as handle:
                header=handle.read(64)
            if len(header)<12 or b'ftyp' not in header:
                raise ValueError('Configured file is not an MP4 container')
        except (OSError,ValueError):
            raise HTTPException(404,'Configured replay MP4 is unavailable or invalid') from None
        return self.path

    def status(self):
        try:
            path=self.checked_path()
            size=path.stat().st_size
        except (HTTPException,OSError):
            return dict(available=False,url=None,media_type='video/mp4',size_bytes=None,pts_offset_ns=self.offset_ns,timestamp_mapping_configured=self.offset_ns is not None,tolerance_ns=self.tolerance_ns)
        return dict(available=True,url='/api/replay/video',media_type='video/mp4',size_bytes=size,pts_offset_ns=self.offset_ns,timestamp_mapping_configured=self.offset_ns is not None,tolerance_ns=self.tolerance_ns)

    def response(self,request: Request):
        path=self.checked_path()
        try:
            file=path.open('rb')
            stat=os.fstat(file.fileno())
        except OSError:
            raise HTTPException(404,'Configured replay MP4 is unavailable') from None
        size=stat.st_size
        headers={'Accept-Ranges':'bytes','Cache-Control':'private, max-age=0','Content-Disposition':'inline; filename="recorded-replay.mp4"','X-Content-Type-Options':'nosniff'}
        start,end,code=0,size-1,200
        range_header=request.headers.get('range')
        if range_header:
            match=re.fullmatch(r'bytes=(\d*)-(\d*)',range_header.strip()) if len(range_header)<=128 else None
            if not match or not any(match.groups()):
                file.close()
                return Response(status_code=416,headers={**headers,'Content-Range':f'bytes */{size}'})
            left,right=match.groups()
            if left:
                start=int(left)
                end=min(int(right),size-1) if right else size-1
            else:
                suffix=int(right)
                start=max(0,size-suffix)
                end=size-1
                if suffix==0:
                    start=size
            if start>=size or start>end:
                file.close()
                return Response(status_code=416,headers={**headers,'Content-Range':f'bytes */{size}'})
            code=206
            headers['Content-Range']=f'bytes {start}-{end}/{size}'
        headers['Content-Length']=str(end-start+1)
        if request.method=='HEAD':
            file.close()
            return Response(status_code=code,headers=headers,media_type='video/mp4')

        def chunks():
            try:
                file.seek(start)
                remaining=end-start+1
                while remaining:
                    data=file.read(min(256*1024,remaining))
                    if not data:
                        break
                    remaining-=len(data)
                    yield data
            finally:
                file.close()
        return StreamingResponse(chunks(),status_code=code,headers=headers,media_type='video/mp4')


class ReplayTimeline:
    def __init__(self,path,camera,video):
        self.video=video
        self.camera=camera
        self.frames=[]
        self.sha256=None
        self.error=None
        self.observations=self.track_count=0
        try:
            if not path:
                raise ValueError('Replay metadata is not configured')
            path=Path(path)
            before=hashlib.sha256(path.read_bytes()).hexdigest()
            frames,self.observations,self.track_count=load_export(path)
            after=hashlib.sha256(path.read_bytes()).hexdigest()
            if before!=after:
                raise ValueError('Replay metadata changed while building read-only timeline')
            self.sha256=before
            sources={frame['source_id'] for frame in frames}
            self.frames=[dict(frame_index=frame['frame_index'],pts_ns=frame['pts_ns'],source_id=frame['source_id'],frame_width=frame['width'],frame_height=frame['height'],camera_id=camera if len(sources)==1 else f"{camera}:{frame['source_id']}",detections=frame['detections'],raw_roi_counts=frame['raw_roi_counts']) for frame in frames]
        except (OSError,ValueError,KeyError,TypeError,OverflowError) as exc:
            # Do not reveal an absolute configured path through API error messages.
            self.error='Configured replay metadata is unavailable or invalid ('+type(exc).__name__+')'

    def payload(self):
        if not self.frames:
            raise HTTPException(422,self.error or 'Replay timeline unavailable')
        media=self.video.status()
        return dict(source='pipegen_replay',synthetic=False,read_only=True,timestamp_basis='original_video_pts_ns',metadata_sha256=self.sha256,total_frames=len(self.frames),person_observations=self.observations,unique_track_ids=self.track_count,first_pts_ns=self.frames[0]['pts_ns'],last_pts_ns=self.frames[-1]['pts_ns'],frame_width=self.frames[0]['frame_width'],frame_height=self.frames[0]['frame_height'],camera_id=self.camera,video_available=media['available'],video_url=media['url'],pts_offset_ns=media['pts_offset_ns'],timestamp_mapping_configured=media['timestamp_mapping_configured'],tolerance_ns=media['tolerance_ns'],frames=self.frames)
