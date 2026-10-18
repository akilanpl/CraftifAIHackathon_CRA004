#!/usr/bin/env python3
"""Audit genuine recorded factory metadata/config without changing either source.

Native occupancy is compared with raw bounding-box bottom centers. It is never
converted into native entry events. This script does not decode or infer video.
"""
import argparse
from collections import Counter, defaultdict
import configparser
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.replay import load_export

DEFAULT_POLYGON=[[.42,.74],[.62,.74],[.62,.86],[.42,.86]]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rectangle(polygon):
    if len(polygon)!=4 or len({tuple(p) for p in polygon})!=4:
        raise ValueError('This independent audit requires four rectangular corners')
    xs,ys=sorted({p[0] for p in polygon}),sorted({p[1] for p in polygon})
    if len(xs)!=2 or len(ys)!=2 or {tuple(p) for p in polygon}!={(x,y) for x in xs for y in ys}:
        raise ValueError('Audit polygon must be axis-aligned; do not silently approximate another shape')
    return xs[0],ys[0],xs[1],ys[1]


def inside(foot,bounds):
    return bounds[0]<=foot[0]<=bounds[2] and bounds[1]<=foot[1]<=bounds[3]


def audit(metadata,analytics_config,polygon=None,threshold=.5,roi_name='RestrictedZone'):
    if not 0<=threshold<=1:
        raise ValueError('Confidence threshold must be normalized')
    metadata,analytics_config=Path(metadata),Path(analytics_config)
    metadata_hash,config_hash=sha(metadata),sha(analytics_config)
    raw=json.loads(metadata.read_text())
    parsed,observations,track_count=load_export(metadata)
    config=configparser.ConfigParser(interpolation=None)
    config.optionxform=str
    config.read_string(analytics_config.read_text())
    width=config.getint('property','config-width');height=config.getint('property','config-height')
    sources={frame['source_id'] for frame in parsed}
    if len(sources)!=1:
        raise ValueError('Factory audit requires one explicitly matching video source')
    source=next(iter(sources))
    section=f'roi-filtering-stream-{source}'
    if config.getint('property','enable')!=1 or config.getint(section,'enable')!=1 or config.getint(section,'class-id')!=0 or config.getint(section,'inverse-roi')!=0:
        raise ValueError('Analytics config does not enable ordinary person ROI occupancy')
    native_coords=[int(value) for value in config.get(section,'roi-'+roi_name).split(';')]
    if len(native_coords)!=8:
        raise ValueError('Analytics ROI must have four explicit rectangular corners')
    native_polygon=list(zip(native_coords[::2],native_coords[1::2]))
    native_bounds=rectangle(native_polygon)
    normalized_polygon=polygon or [[x/width,y/height] for x,y in native_polygon]
    normalized_bounds=rectangle(normalized_polygon)
    expected_pixels=[[round(x*width),round(y*height)] for x,y in normalized_polygon]
    config_matches=expected_pixels==[list(point) for point in native_polygon]
    transitions=Counter({key:0 for key in ['first_observed_inside','first_observed_outside','observed_entries','observed_reentries','observed_exits','hold_observations']})
    states={};events=[];transition_events=[];gaps=[];per_track=defaultdict(lambda:{'observations':0,'confidence_eligible_observations':0,'inside_observations':0,'first_frame':None,'last_frame':None,'gaps':0,'max_missing_frames':0})
    counts=Counter();disagreements=[];frame_counts=[]
    for frame in raw['frames']:
        if (frame['width'],frame['height'])!=(width,height):
            raise ValueError('Metadata dimensions differ from analytics config')
        native_values=[record['roi_counts'][roi_name] for record in frame['analytics'] if roi_name in record.get('roi_counts',{})]
        if len(native_values)!=1:
            raise ValueError('Every audited frame must have one unambiguous native ROI occupancy count')
        native_count=native_values[0]
        all_box_count=eligible_count=config_geometry_count=0
        for obj in frame['objects']:
            if obj['class_id']!=0 or obj['label'].lower()!='person':continue
            box=obj['bbox'];foot=(box['left']+box['width']/2,box['top']+box['height'])
            normalized=(foot[0]/width,foot[1]/height)
            is_inside=inside(normalized,normalized_bounds)
            all_box_count+=int(is_inside)
            config_geometry_count+=int(inside(foot,native_bounds))
            eligible=obj['confidence']>=threshold
            eligible_count+=int(is_inside and eligible)
            raw_id=obj.get('id')
            if type(raw_id) is not int or not 0<=raw_id<2**64-1:
                counts['missing_track_observations']+=1;continue
            track=str(raw_id);key=(source,track)
            previous=states.get(key)
            summary=per_track[track];summary['observations']+=1
            if summary['last_frame'] is not None and frame['frame']>summary['last_frame']+1:
                missing=frame['frame']-summary['last_frame']-1
                gaps.append(dict(track_id=track,last_seen_frame=summary['last_frame'],reappeared_frame=frame['frame'],missing_frames=missing,gap_pts_ns=frame['pts_ns']-summary['last_pts_ns']))
                summary['gaps']+=1;summary['max_missing_frames']=max(summary['max_missing_frames'],missing)
            if summary['first_frame'] is None:summary['first_frame']=frame['frame']
            summary['last_frame'],summary['last_pts_ns']=frame['frame'],frame['pts_ns']
            if not eligible:continue
            summary['confidence_eligible_observations']+=1;summary['inside_observations']+=int(is_inside)
            basis=None
            if is_inside:
                if previous is None:transitions['first_observed_inside']+=1;basis='first_observed_inside'
                elif not previous['inside']:
                    transitions['observed_entries']+=1;basis='observed_outside_to_inside'
                    if previous['ever_inside']:transitions['observed_reentries']+=1
                else:transitions['hold_observations']+=1
            elif previous and previous['inside']:transitions['observed_exits']+=1
            elif previous is None:transitions['first_observed_outside']+=1
            if previous and previous['inside'] and not is_inside:
                transition_events.append(dict(event_type='observed_exit',frame_index=frame['frame'],pts_ns=frame['pts_ns'],track_id=track))
            if basis:
                transition_events.append(dict(event_type='observed_reentry' if previous and previous['ever_inside'] else basis,frame_index=frame['frame'],pts_ns=frame['pts_ns'],track_id=track))
                events.append(dict(frame_index=frame['frame'],pts_ns=frame['pts_ns'],source_id=source,track_id=track,confidence=obj['confidence'],entry_basis=basis,bottom_center_normalized=list(normalized)))
            states[key]=dict(inside=is_inside,ever_inside=is_inside or bool(previous and previous['ever_inside']))
        counts['native_compared_frames']+=1
        counts['native_vs_actual_config_disagreeing_frames']+=int(native_count!=config_geometry_count)
        counts['native_vs_app_polygon_all_boxes_disagreeing_frames']+=int(native_count!=all_box_count)
        counts['native_vs_app_polygon_confidence_filtered_disagreeing_frames']+=int(native_count!=eligible_count)
        counts['app_vs_rounded_native_polygon_disagreeing_frames']+=int(all_box_count!=config_geometry_count)
        if native_count!=all_box_count or native_count!=eligible_count or native_count!=config_geometry_count:
            disagreements.append(dict(frame_index=frame['frame'],pts_ns=frame['pts_ns'],native=native_count,actual_config_geometry=config_geometry_count,app_all_boxes=all_box_count,app_confidence_filtered=eligible_count))
        frame_counts.append(dict(frame_index=frame['frame'],pts_ns=frame['pts_ns'],native_roi_count=native_count,app_occupancy=eligible_count))
    unchanged=sha(metadata)==metadata_hash and sha(analytics_config)==config_hash
    if not unchanged:raise ValueError('Audit source changed while reading')
    return dict(dataset='factory',source='genuine recorded PipeGen metadata',synthetic=False,verification_scope='CPU read-only metadata/config audit; no inference, video decoding or identity verification',metadata_sha256=metadata_hash,analytics_config_sha256=config_hash,input_unchanged=unchanged,total_frames=len(parsed),person_observations=observations,unique_tracker_ids=track_count,source_id=source,frame_width=width,frame_height=height,first_pts_ns=parsed[0]['pts_ns'],last_pts_ns=parsed[-1]['pts_ns'],confidence_threshold=threshold,metadata_min_confidence=raw.get('min_confidence'),app_polygon=normalized_polygon,requested_polygon=DEFAULT_POLYGON,config_matches_requested_polygon_at_integer_pixel_rounding=[[round(x*width),round(y*height)] for x,y in DEFAULT_POLYGON]==[list(point) for point in native_polygon],native_roi_name=roi_name,native_roi_polygon_pixels=[list(point) for point in native_polygon],app_polygon_rounded_pixels=expected_pixels,config_matches_app_polygon_at_integer_pixel_rounding=config_matches,computed_alerts=len(events),observed_track_transitions=dict(transitions),native_roi_geometry_comparison=dict(counts),disagreements=disagreements,computed_incidents=events,observed_transition_timeline=transition_events,comparison_note='Native ROI occupancy and application geometry differ in some frames; the cause is not established by this metadata alone. Native counts are preserved and are not asserted to be zone-entry events.',track_gap_audit=dict(tracks_with_gaps=sum(value['gaps']>0 for value in per_track.values()),total_gap_reappearances=len(gaps),gaps=gaps,per_track=dict(per_track),interpretation='Missing observations are not exits; recurring IDs after gaps do not verify identity or prove tracker-ID reuse.'),frame_occupancy=frame_counts)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('metadata',type=Path)
    parser.add_argument('--analytics-config',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--confidence-threshold',type=float,default=.5)
    parser.add_argument('--roi-name',default='RestrictedZone')
    args=parser.parse_args()
    inputs=(args.metadata,args.analytics_config)
    if args.report.resolve() in tuple(path.resolve() for path in inputs) or (args.report.exists() and any(args.report.samefile(path) for path in inputs)):
        raise SystemExit('Refusing to overwrite audit input')
    report=audit(args.metadata,args.analytics_config,threshold=args.confidence_threshold,roi_name=args.roi_name)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:report[key] for key in ['metadata_sha256','total_frames','person_observations','unique_tracker_ids','computed_alerts','observed_track_transitions','native_roi_geometry_comparison','config_matches_app_polygon_at_integer_pixel_rounding']},indent=2))


if __name__=='__main__':main()
