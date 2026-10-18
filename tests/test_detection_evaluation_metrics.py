"""Hand-computed evaluator fixtures, not claims about real model accuracy."""
from copy import deepcopy
import json
import math

import pytest

from evaluation.metrics import evaluate_detections, intersection_over_union


BOX = [.1, .1, .4, .4]
OTHER = [.6, .6, .9, .9]


def annotation(box=BOX, class_name='person'):
    return dict(class_name=class_name, bbox=list(box))


def image(image_id='a', boxes=None, *, reviewed=True, source='human_manual'):
    return dict(image_id=image_id, width=100, height=80,
                reviewed_by_human=reviewed, annotation_source=source,
                ground_truth=[annotation(box) for box in (boxes if boxes is not None else [BOX])])


def prediction(image_id='a', box=BOX, confidence=.9, class_name='person'):
    return dict(image_id=image_id, class_name=class_name, bbox=list(box), confidence=confidence)


def at(report, threshold=.5):
    return next(row for row in report['thresholds'] if row['confidence_threshold'] == threshold)


def test_iou_known_geometry_identical_disjoint_and_touching_boundaries():
    assert intersection_over_union([0, 0, .5, .5], [.25, 0, .75, .5]) == pytest.approx(1/3)
    assert intersection_over_union(BOX, BOX) == pytest.approx(1)
    assert intersection_over_union(BOX, OTHER) == 0
    assert intersection_over_union([0, 0, .5, .5], [.5, 0, 1, .5]) == 0


def test_perfect_person_predictions_get_perfect_counts_and_all_ten_aps():
    report = evaluate_detections([image()], [prediction()])
    assert report['status'] == 'COMPLETE'
    assert report['formal_metrics_available'] is True
    assert {key: at(report)[key] for key in ('tp', 'fp', 'fn', 'precision', 'recall', 'f1')} == {
        'tp': 1, 'fp': 0, 'fn': 0, 'precision': 1, 'recall': 1, 'f1': 1,
    }
    assert [row['iou_threshold'] for row in report['ap_by_iou']] == [.5, .55, .6, .65, .7, .75, .8, .85, .9, .95]
    assert report['ap50'] == report['map50_95'] == 1


def test_unreviewed_empty_ground_truth_is_unknown_not_a_reviewed_negative():
    report = evaluate_detections([image(boxes=[], reviewed=False)], [prediction(confidence=.3)])
    assert report['status'] == 'REVIEW_REQUIRED'
    assert report['formal_metrics_available'] is False
    assert report['ground_truth_person_count'] is None
    assert report['review_required_image_ids'] == ['a']
    assert at(report)['threshold_rejection_count'] == 1
    assert at(report, .25)['retained_prediction_count'] == 1
    for row in report['thresholds']:
        assert all(row[key] is None for key in ('tp', 'fp', 'fn', 'precision', 'recall', 'f1'))
    assert report['ap50'] is report['map50_95'] is None
    assert all(row['ap'] is None for row in report['ap_by_iou'])


def test_one_unreviewed_image_blocks_whole_dataset_instead_of_silently_evaluating_subset():
    report = evaluate_detections([image('a'), image('b', [], reviewed=False)], [prediction()])
    assert report['human_reviewed_image_count'] == 1
    assert report['review_required_image_ids'] == ['b']
    assert at(report)['tp'] is None
    assert report['ap50'] is None


def test_human_review_flag_without_manual_annotation_provenance_does_not_unlock_metrics():
    report = evaluate_detections([image(source='not_reported')], [prediction()])
    assert report['formal_metrics_available'] is False
    assert 'annotation_source must be human_manual' in report['review_issues']['a']


@pytest.mark.parametrize('source', ['model_predictions', 'detector', 'predictions', 'pseudo_labels'])
def test_model_predictions_are_rejected_as_ground_truth_even_when_marked_reviewed(source):
    with pytest.raises(ValueError, match='cannot be ground truth'):
        evaluate_detections([image(source=source)], [prediction()])


def test_reusing_prediction_shaped_records_as_ground_truth_is_rejected():
    item = image()
    item['ground_truth'] = [prediction()]
    with pytest.raises(ValueError, match='confidence records cannot be ground truth'):
        evaluate_detections([item], [prediction()])


def test_reviewed_empty_gt_has_undefined_ap_even_if_false_positives_exist():
    report = evaluate_detections([image(boxes=[])], [prediction()])
    assert report['formal_metrics_available'] is True
    assert (at(report)['tp'], at(report)['fp'], at(report)['fn']) == (0, 1, 0)
    assert at(report)['precision'] == 0
    assert at(report)['recall'] is None
    assert at(report)['f1'] == 0
    assert report['ap50'] is report['map50_95'] is None


def test_empty_predictions_with_gt_have_zero_recall_and_ap_but_precision_is_undefined():
    report = evaluate_detections([image()], [])
    assert (at(report)['tp'], at(report)['fp'], at(report)['fn']) == (0, 0, 1)
    assert at(report)['precision'] is None
    assert at(report)['recall'] == at(report)['f1'] == report['ap50'] == report['map50_95'] == 0
    negative = evaluate_detections([image(boxes=[])], [])
    assert all(at(negative)[key] is None for key in ('precision', 'recall', 'f1'))
    assert negative['ap50'] is None


def test_duplicate_predictions_are_not_deduplicated_and_only_one_matches_each_gt():
    report = evaluate_detections([image()], [prediction(confidence=.9), prediction(confidence=.8)])
    assert (at(report)['tp'], at(report)['fp'], at(report)['fn']) == (1, 1, 0)
    assert at(report)['precision'] == .5
    assert at(report)['f1'] == pytest.approx(2/3)
    # Ranking AP can remain perfect when the duplicate ranks after complete recall.
    assert report['ap50'] == 1


def test_matching_is_per_image_and_person_class_not_just_spatial_overlap():
    report = evaluate_detections([image('a'), image('b', [])], [prediction('b'), prediction('a', class_name='forklift')])
    assert (at(report)['tp'], at(report)['fp'], at(report)['fn']) == (0, 1, 1)
    assert report['ignored_nonperson_prediction_count'] == 1
    assert report['ap50'] == 0


def test_confidence_thresholds_include_equality_and_filter_rejections_are_prediction_statistics():
    report = evaluate_detections([image(boxes=[BOX, OTHER])], [prediction(confidence=.5), prediction(box=OTHER, confidence=.25)])
    assert [row['confidence_threshold'] for row in report['thresholds']] == [.25, .4, .5, .6, .7]
    assert (at(report, .25)['tp'], at(report, .25)['fn']) == (2, 0)
    assert (at(report, .5)['tp'], at(report, .5)['fn']) == (1, 1)
    assert at(report, .5)['threshold_rejection_count'] == 1
    assert at(report, .6)['retained_prediction_count'] == 0


def test_ap_uses_predictions_below_operating_point_thresholds_without_silent_prefilter():
    report = evaluate_detections([image()], [prediction(confidence=.01)])
    assert all(row['tp'] == 0 for row in report['thresholds'])
    assert report['ap50'] == report['map50_95'] == 1


def test_101_point_ap_hand_computed_tp_fp_tp_and_global_confidence_ranking():
    # Two images, two GTs. After global ranking: TP(.9), FP(.8), TP(.7).
    # Interpolated precision is 1 for recall 0..0.50 (51 points),
    # then 2/3 for recall .51..1.00 (50 points).
    predictions = [prediction('b', confidence=.7), prediction('a', confidence=.9), prediction('a', box=OTHER, confidence=.8)]
    report = evaluate_detections([image('a'), image('b')], predictions)
    expected = (51 + 50*2/3)/101
    assert report['ap50'] == pytest.approx(expected)
    assert report['map50_95'] == pytest.approx(expected)
    assert (at(report)['tp'], at(report)['fp'], at(report)['fn']) == (2, 1, 0)
    assert at(report)['precision'] == pytest.approx(2/3)
    assert at(report)['f1'] == pytest.approx(.8)


def test_101_point_ap_with_unreached_recall_is_not_voc_continuous_integration():
    # One of two GTs detected; 51 of 101 recall points have precision 1.
    report = evaluate_detections([image(boxes=[BOX, OTHER])], [prediction()])
    assert report['ap50'] == pytest.approx(51/101)


def test_iou_sweep_changes_ap_at_correct_thresholds():
    # GT area .5*.5; prediction .3*.5 fully inside => IoU exactly .6.
    report = evaluate_detections([image(boxes=[[0, 0, .5, .5]])], [prediction(box=[0, 0, .3, .5])])
    assert report['ap50'] == 1
    assert [row['ap'] for row in report['ap_by_iou']] == [1, 1, 1, 0, 0, 0, 0, 0, 0, 0]
    assert report['map50_95'] == pytest.approx(.3)


def test_greedy_match_uses_highest_iou_unmatched_box_and_never_matches_gt_twice():
    gt_a = [0, 0, .4, .4]
    gt_b = [.2, 0, .6, .4]
    report = evaluate_detections([image(boxes=[gt_a, gt_b])], [prediction(box=gt_a, confidence=.9), prediction(box=gt_b, confidence=.8), prediction(box=gt_a, confidence=.7)])
    assert (at(report)['tp'], at(report)['fp'], at(report)['fn']) == (2, 1, 0)


def test_tied_confidence_is_stable_input_order_and_inputs_are_not_mutated():
    images = [image()]
    predictions = [prediction(box=OTHER, confidence=.9), prediction(confidence=.9)]
    original = deepcopy((images, predictions))
    assert evaluate_detections(images, predictions)['ap50'] == pytest.approx(.5)
    assert evaluate_detections(images, list(reversed(predictions)))['ap50'] == 1
    assert (images, predictions) == original


@pytest.mark.parametrize('bbox', [[0, 0, 0, 1], [.5, 0, .4, .8], [-.1, 0, .5, .5], [0, 0, 1.1, 1], [0, math.nan, 1, 1], [0, 0, math.inf, 1], [False, 0, 1, 1], [0, 0, 1], 'not-a-box', [0, 0, 10**1000, 1]])
def test_malformed_prediction_geometry_is_rejected(bbox):
    with pytest.raises(ValueError):
        evaluate_detections([image()], [prediction(box=bbox)])


@pytest.mark.parametrize('confidence', [-.1, 1.1, math.nan, math.inf, True, '0.5'])
def test_confidence_limits_and_finiteness(confidence):
    with pytest.raises(ValueError):
        evaluate_detections([image()], [prediction(confidence=confidence)])


def test_duplicate_ids_duplicate_gt_unknown_images_and_invalid_dimensions_are_rejected():
    with pytest.raises(ValueError, match='Duplicate image_id'):
        evaluate_detections([image(), image()], [])
    with pytest.raises(ValueError, match='duplicate ground-truth'):
        evaluate_detections([image(boxes=[BOX, BOX])], [])
    with pytest.raises(ValueError, match='unknown image_id'):
        evaluate_detections([image()], [prediction('not-in-review-set')])
    for width in (0, -1, 1.5, True):
        invalid = image()
        invalid['width'] = width
        with pytest.raises(ValueError, match='positive integer'):
            evaluate_detections([invalid], [])


def test_invalid_review_markers_thresholds_and_empty_dataset_are_rejected():
    invalid = image()
    invalid['reviewed_by_human'] = 'true'
    with pytest.raises(ValueError, match='boolean'):
        evaluate_detections([invalid], [])
    for thresholds in ([], [.5, .5], [math.nan], [-1], [True], '0.5'):
        with pytest.raises(ValueError):
            evaluate_detections([image()], [], confidence_thresholds=thresholds)
    with pytest.raises(ValueError, match='At least one'):
        evaluate_detections([], [])


def test_output_is_strict_json_safe_for_review_gated_and_complete_reports():
    for images, predictions in [([image(reviewed=False)], [prediction()]), ([image(boxes=[])], []), ([image()], [prediction()])]:
        report = evaluate_detections(images, predictions)
        assert json.loads(json.dumps(report, allow_nan=False))['status'] == report['status']
