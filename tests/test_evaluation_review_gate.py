"""Approval/source gates for the new evaluation CLI; synthetic annotation fixtures only."""
import copy
import pytest
from evaluation.run_evaluation import load_review


def package():
    row=dict(image_id='frame0',width=960,height=540,image_sha256='fixture-hash')
    manifest=dict(dataset_id='fixture-dataset',source_video_sha256='fixture-source',images=[row])
    annotations=dict(dataset_id='fixture-dataset',source_video_sha256='fixture-source',images=[dict(**row,annotation_source='human_manual',reviewed_by_human=True,reviewed_by='Human test fixture',reviewed_at='2026-10-18T00:00:00Z',ground_truth=[])],human_review_record=dict(complete=True,status='HUMAN_REVIEW_COMPLETE',reviewer_name='Human test fixture',method='human_manual_boxes_without_predictions',model_predictions_used_as_ground_truth=False))
    return manifest,annotations


def test_complete_matching_human_attestation_is_required():
    manifest,annotations=package();images,accepted,_=load_review(manifest,annotations)
    assert accepted and images[0]['reviewed_by_human']
    annotations['human_review_record']['complete']=False
    images,accepted,_=load_review(manifest,annotations)
    assert not accepted and not images[0]['reviewed_by_human']
    assert annotations['images'][0]['reviewed_by_human']  # input record never mutated


@pytest.mark.parametrize('field,value', [('reviewer_name',''),('method','model_assisted'),('status','PENDING'),('model_predictions_used_as_ground_truth',True)])
def test_incomplete_or_prediction_based_review_is_not_formal(field,value):
    manifest,annotations=package();annotations['human_review_record'][field]=value
    images,accepted,_=load_review(manifest,annotations)
    assert not accepted and not images[0]['reviewed_by_human']


@pytest.mark.parametrize('field,value',[('source_video_sha256','other-video'),('dataset_id','other-dataset')])
def test_source_mismatch_is_rejected(field,value):
    manifest,annotations=package();annotations[field]=value
    with pytest.raises(ValueError,match='mismatch'):load_review(manifest,annotations)


@pytest.mark.parametrize('field,value',[('image_sha256','different-pixels'),('width',1280),('image_id','other-frame')])
def test_annotation_pixels_and_dimensions_must_match(field,value):
    manifest,annotations=package();annotations['images'][0][field]=value
    with pytest.raises(ValueError):load_review(manifest,annotations)
