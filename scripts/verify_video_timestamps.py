"""CPU-only GStreamer timing audit of an explicitly paired MP4 and PipeGen export.

Run with the system Python that provides gi/GStreamer, not the app virtualenv.
This verifies timing, never model inference or the provenance of a claimed pair.
"""
import argparse
import hashlib
import json
from pathlib import Path
import gi

gi.require_version('Gst','1.0')
from gi.repository import Gst


def digest(path):
    value=hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''):
            value.update(chunk)
    return value.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video',type=Path)
    parser.add_argument('metadata',type=Path)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    video_hash,metadata_hash=digest(args.video),digest(args.metadata)
    frames=json.loads(args.metadata.read_text())['frames']
    assert frames and len({f['source_id'] for f in frames})==1, 'Require one explicit source'
    Gst.init(None)
    pipeline=Gst.Pipeline.new('cpu-timestamp-audit')
    names=['filesrc','qtdemux','h264parse','avdec_h264','appsink']
    elements=[Gst.ElementFactory.make(name) for name in names]
    assert all(elements), 'Existing GStreamer H264 CPU decoder and appsink are required'
    source,demux,parse,decode,sink=elements
    source.set_property('location',str(args.video.resolve()))
    sink.set_property('sync',False);sink.set_property('max-buffers',4);sink.set_property('drop',False)
    for element in elements:pipeline.add(element)
    assert source.link(demux) and parse.link(decode) and decode.link(sink)
    def pad_added(_demux,pad):
        caps=pad.get_current_caps()
        if caps and caps.to_string().startswith('video/x-h264'):
            assert pad.link(parse.get_static_pad('sink'))==Gst.PadLinkReturn.OK
    demux.connect('pad-added',pad_added)
    count=0;offsets=set();segments=set();samples=[]
    sample_indices={0,len(frames)//4,len(frames)//2,3*len(frames)//4,len(frames)-1}
    pipeline.set_state(Gst.State.PLAYING)
    try:
        while True:
            sample=sink.emit('try-pull-sample',10*Gst.SECOND)
            if sample is None:break
            assert count<len(frames), 'Video has more frames than metadata'
            buffer=sample.get_buffer();segment=sample.get_segment()
            frame=frames[count];caps=sample.get_caps().get_structure(0)
            assert (caps.get_value('width'),caps.get_value('height'))==(frame['width'],frame['height']), 'Source dimensions differ'
            stream_time=segment.to_stream_time(Gst.Format.TIME,buffer.pts)
            assert stream_time!=Gst.CLOCK_TIME_NONE, 'Invalid stream timestamp'
            offsets.add(frame['pts_ns']-stream_time)
            segments.add((segment.start,segment.time))
            if count in sample_indices:
                samples.append(dict(frame_index=frame['frame'],decoded_index=count,video_pts_ns=buffer.pts,metadata_pts_ns=frame['pts_ns'],stream_time_ns=stream_time))
            count+=1
        terminal=pipeline.get_bus().timed_pop_filtered(Gst.SECOND,Gst.MessageType.ERROR|Gst.MessageType.EOS)
        assert terminal is not None and terminal.type==Gst.MessageType.EOS, 'CPU decode failed or timed out before end of stream'
        assert count==len(frames), 'Video/metadata frame counts differ'
        assert len(offsets)==1, 'No constant metadata-to-media timestamp offset; investigate variable source transforms'
    finally:
        pipeline.set_state(Gst.State.NULL)
    assert digest(args.video)==video_hash and digest(args.metadata)==metadata_hash, 'Input changed during audit'
    result=dict(video_sha256=video_hash,metadata_sha256=metadata_hash,decoded_frames=count,metadata_frames=len(frames),verified_pts_offset_ns=offsets.pop(),segments=[dict(start_ns=a,time_ns=b) for a,b in sorted(segments)],samples=samples,input_unchanged=True,method='Existing GStreamer CPU decoder; every decoded frame dimensions and stream timestamp compared by export order. Browser presented mediaTime must additionally be verified.',limitation='Timing equivalence does not prove these files came from the same execution; preserve the run configuration and source hashes.')
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
