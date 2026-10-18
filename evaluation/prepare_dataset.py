#!/usr/bin/env python3
"""Decode a new, externally stored human-review dataset. Never reads model metadata."""
import argparse
from datetime import datetime,timezone
import hashlib,json,os,shutil
from pathlib import Path
import gi

gi.require_version('Gst','1.0')
from gi.repository import Gst


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def pipeline(video,jpeg=False):
    description='filesrc name=input ! qtdemux ! h264parse ! avdec_h264 ! '
    if jpeg:description+='videoconvert ! videoscale ! video/x-raw,width=960,height=540 ! jpegenc quality=85 ! '
    result=Gst.parse_launch(description+'appsink name=sink sync=false max-buffers=2 drop=false')
    result.get_by_name('input').set_property('location',str(video))
    return result,result.get_by_name('sink')


def samples(video,jpeg=False):
    run,sink=pipeline(video,jpeg);run.set_state(Gst.State.PLAYING)
    try:
        index=0
        while True:
            sample=sink.emit('try-pull-sample',10*Gst.SECOND)
            if sample is None:
                error=run.get_bus().pop_filtered(Gst.MessageType.ERROR)
                if error:raise RuntimeError(str(error.parse_error()[0]))
                if not sink.get_property('eos'):raise RuntimeError('CPU video decoding timed out')
                break
            yield index,sample
            index+=1
    finally:run.set_state(Gst.State.NULL)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();video=args.video.resolve(strict=True);target=args.output.resolve()
    if target.exists():raise SystemExit('Refusing existing dataset directory; reviewed annotations/images are never overwritten')
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.parent.stat().st_dev==Path('/').stat().st_dev:raise SystemExit('Dataset must be on external storage')
    if shutil.disk_usage('/').free<1024**3 or shutil.disk_usage(target.parent).free<20*1024**3:raise SystemExit('Storage reserve is below required limits')
    source_hash=digest(video)
    if source_hash!='14fb11cda9d031b497755195c04f6781df3a579d9044155114a3923cc5f43671':raise SystemExit('Dataset is scoped to the verified warehouse source; different footage requires separate attribution and review setup')
    Gst.init(None);timing=[]
    for index,sample in samples(video):
        buffer=sample.get_buffer();segment=sample.get_segment();caps=sample.get_caps().get_structure(0)
        timing.append(dict(frame_index=index,pts_ns=int(buffer.pts),media_timestamp_seconds=segment.to_stream_time(Gst.Format.TIME,buffer.pts)/1e9,source_width=caps.get_value('width'),source_height=caps.get_value('height')))
    if len(timing)<30:raise SystemExit('At least30 distinct decoded frames are required')
    count=min(40,len(timing));selected={round(i*(len(timing)-1)/(count-1)) for i in range(count)}
    if len(timing)>106:selected.add(106)  # previously observed shelving case, not a GT label
    target.mkdir();(target/'frames').mkdir();images=[]
    for index,sample in samples(video,True):
        if index not in selected:continue
        buffer=sample.get_buffer();ok,mapped=buffer.map(Gst.MapFlags.READ)
        if not ok:raise RuntimeError('Unable to map JPEG')
        pixels=bytes(mapped.data);buffer.unmap(mapped)
        relative=f'frames/frame-{index:03}.jpg';path=target/relative;path.write_bytes(pixels)
        images.append(dict(image_id=f'warehouse-frame-{index:03}',path=relative,width=960,height=540,image_sha256=digest(path),**timing[index]))
    assert len(images)==len(selected)
    manifest=dict(schema_version=1,dataset_id='warehouse-independent-review-'+source_hash[:12],prepared_at=datetime.now(timezone.utc).isoformat(),source_video_name=video.name,source_video_sha256=source_hash,source_frame_count=len(timing),image_count=len(images),independently_human_reviewed_images=0,selection='40uniformly spaced decoded frames plus frame106 shelving-review candidate; no predictions used for annotations',preprocessing='CPU GStreamer H264 decode;960x540;JPEGquality85; model preprocessing unchanged',source={'title':'Men Working in a Warehouse','creator':'Tiger Lily','source_page':'https://www.pexels.com/video/men-working-in-a-warehouse-4281405/','license':'https://www.pexels.com/license/','attribution_basis':'Existing source release manifest; footage is not relicensed as code'},limitations=['One short moving-camera video, not independent held-out workplaces','No claim of broad lighting or distant-person coverage; reviewers must characterize actual content','No human labels yet; ground truth is UNKNOWN, not negative','Empty late-video frames and partial people are retained'],images=images)
    annotations=dict(schema_version=1,dataset_id=manifest['dataset_id'],source_video_sha256=source_hash,human_review_record={'status':'PENDING','reviewer_name':None,'complete':False,'model_predictions_used_as_ground_truth':False},images=[dict(image_id=i['image_id'],width=i['width'],height=i['height'],image_sha256=i['image_sha256'],reviewed_by_human=False,annotation_source='human_manual',reviewed_by=None,reviewed_at=None,ground_truth=[]) for i in images])
    (target/'dataset-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(target/'annotations.json').write_text(json.dumps(annotations,indent=2)+'\n')
    shutil.copyfile(Path(__file__).with_name('review.html'),target/'index.html')
    print(json.dumps({'dataset':str(target),'images':len(images),'human_reviewed':0,'accuracy':'PENDING HUMAN REVIEW','source_sha256':source_hash},indent=2))


if __name__=='__main__':main()
