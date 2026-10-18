"""Person detection evaluation over supplied, bounded prediction records.

Boxes are normalized [x1, y1, x2, y2]. Matching is confidence ordered,
class/image specific, greedy to the highest-IoU unmatched human annotation.
AP uses 101 interpolated recall points and ALL supplied person predictions,
independently of the confidence thresholds used for operating-point summaries.
No predictions are promoted to ground truth. Unreviewed images have UNKNOWN
annotations, including when their draft ground_truth array is empty.

This is a person-only evaluator, not the full COCO evaluator: crowd, ignore,
area ranges and COCO maxDets categories are not implemented. AP is conditional
on the predictions supplied by the caller; detector confidence floors and
candidate caps must be reported separately and can limit attainable recall.
"""
from collections.abc import Iterable, Mapping, Sequence
from math import isfinite
from numbers import Real
from typing import Any

DEFAULT_CONFIDENCE_THRESHOLDS = (.25, .4, .5, .6, .7)
AP_IOU_THRESHOLDS = tuple(round(.5 + .05 * index, 2) for index in range(10))
FORBIDDEN_GROUND_TRUTH_SOURCES = frozenset({
    'model', 'detector', 'prediction', 'predictions', 'model_predictions',
    'predicted', 'pseudo_labels', 'detector_predictions',
})


def _number(value: Any, field: str, *, minimum: float = 0., maximum: float = 1.) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f'{field} must be a finite number')
    try:
        result = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError(f'{field} must be a finite number') from error
    if not isfinite(result):
        raise ValueError(f'{field} must be a finite number')
    if not minimum <= result <= maximum:
        raise ValueError(f'{field} must be in [{minimum}, {maximum}]')
    return result


def _box(value: Any, field: str) -> tuple[float, float, float, float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 4:
        raise ValueError(f'{field} must be normalized [x1, y1, x2, y2]')
    x1, y1, x2, y2 = (_number(number, field) for number in value)
    if x1 >= x2 or y1 >= y2:
        raise ValueError(f'{field} must have positive width and height')
    return x1, y1, x2, y2


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{field} must be a nonempty string')
    return value


def _record(value: Any, field: str) -> Mapping:
    if not isinstance(value, Mapping):
        raise ValueError(f'{field} must be an object')
    return value


def _iou(a: tuple, b: tuple) -> float:
    width = max(0., min(a[2], b[2]) - max(a[0], b[0]))
    height = max(0., min(a[3], b[3]) - max(a[1], b[1]))
    intersection = width * height
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - intersection
    return intersection / union


def intersection_over_union(box_a: Sequence, box_b: Sequence) -> float:
    """Validate normalized nondegenerate boxes, then compute their IoU."""
    return _iou(_box(box_a, 'box_a'), _box(box_b, 'box_b'))


def _prepare(images: Iterable, predictions: Iterable, person_class: str):
    image_map = {}
    ground_truth = {}
    review_required = []
    review_issues = {}
    reviewed_count = 0
    for index, raw in enumerate(images):
        image = _record(raw, f'images[{index}]')
        image_id = _text(image.get('image_id'), 'image_id')
        if image_id in image_map:
            raise ValueError(f'Duplicate image_id: {image_id}')
        for field in ('width', 'height'):
            value = image.get(field)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f'{image_id}.{field} must be a positive integer')
        reviewed = image.get('reviewed_by_human')
        if not isinstance(reviewed, bool):
            raise ValueError(f'{image_id}.reviewed_by_human must be a boolean')
        source = image.get('annotation_source')
        if isinstance(source, str) and source.strip().lower() in FORBIDDEN_GROUND_TRUTH_SOURCES:
            raise ValueError(f'{image_id}: detector predictions cannot be ground truth')
        issues = []
        if not reviewed:
            issues.append('Human review has not been approved')
        if source != 'human_manual':
            issues.append('annotation_source must be human_manual')
        if issues:
            review_required.append(image_id)
            review_issues[image_id] = issues
        else:
            reviewed_count += 1
        annotations = image.get('ground_truth')
        if not isinstance(annotations, list):
            raise ValueError(f'{image_id}.ground_truth must be a list; [] is only a draft until reviewed')
        seen = set()
        person_boxes = []
        for item_index, raw_annotation in enumerate(annotations):
            annotation = _record(raw_annotation, f'{image_id}.ground_truth[{item_index}]')
            if 'confidence' in annotation:
                raise ValueError(f'{image_id}: prediction-shaped confidence records cannot be ground truth')
            if str(annotation.get('annotation_source', '')).strip().lower() in FORBIDDEN_GROUND_TRUTH_SOURCES:
                raise ValueError(f'{image_id}: detector predictions cannot be ground truth')
            class_name = _text(annotation.get('class_name'), 'ground_truth.class_name')
            box = _box(annotation.get('bbox'), 'ground_truth.bbox')
            identity = class_name, box
            if identity in seen:
                raise ValueError(f'{image_id}: duplicate ground-truth box for class {class_name}')
            seen.add(identity)
            if class_name == person_class:
                person_boxes.append(box)
        # An empty unreviewed list remains unknown; no formal metrics use it.
        ground_truth[image_id] = person_boxes
        image_map[image_id] = image
    if not image_map:
        raise ValueError('At least one evaluation image is required')
    prepared = []
    ignored = 0
    for index, raw in enumerate(predictions):
        prediction = _record(raw, f'predictions[{index}]')
        image_id = _text(prediction.get('image_id'), 'prediction.image_id')
        if image_id not in image_map:
            raise ValueError(f'Prediction references unknown image_id: {image_id}')
        class_name = _text(prediction.get('class_name'), 'prediction.class_name')
        box = _box(prediction.get('bbox'), 'prediction.bbox')
        confidence = _number(prediction.get('confidence'), 'prediction.confidence')
        if class_name != person_class:
            ignored += 1
            continue
        # Duplicate predictions remain separate detections and can become FPs.
        prepared.append({'image_id': image_id, 'bbox': box, 'confidence': confidence, 'order': index})
    prepared.sort(key=lambda item: (-item['confidence'], item['order']))
    return image_map, ground_truth, review_required, review_issues, reviewed_count, prepared, ignored


def _match(predictions: list, ground_truth: dict, iou_threshold: float) -> list[int]:
    used = {image_id: set() for image_id in ground_truth}
    labels = []
    for prediction in predictions:
        image_id = prediction['image_id']
        best_index = None
        best_iou = -1.
        for index, box in enumerate(ground_truth[image_id]):
            if index in used[image_id]:
                continue
            overlap = _iou(prediction['bbox'], box)
            if overlap >= iou_threshold and overlap > best_iou:
                best_iou = overlap
                best_index = index
        if best_index is None:
            labels.append(0)
        else:
            used[image_id].add(best_index)
            labels.append(1)
    return labels


def _average_precision(labels: list[int], total_ground_truth: int) -> float | None:
    if total_ground_truth == 0:
        return None
    if not labels:
        return 0.
    true_positive = 0
    precision_recall = []
    for count, label in enumerate(labels, 1):
        true_positive += label
        precision_recall.append((true_positive / total_ground_truth, true_positive / count))
    # Monotone precision envelope implements max precision at recall >= r.
    envelope = []
    best_precision = 0.
    for recall, precision in reversed(precision_recall):
        best_precision = max(best_precision, precision)
        envelope.append((recall, best_precision))
    envelope.reverse()
    interpolated = []
    for point in range(101):
        recall_target = point / 100
        interpolated.append(next((precision for recall, precision in envelope if recall >= recall_target), 0.))
    return sum(interpolated) / 101


def evaluate_detections(
    images: Iterable[Mapping],
    predictions: Iterable[Mapping],
    *,
    confidence_thresholds: Sequence[float] = DEFAULT_CONFIDENCE_THRESHOLDS,
    person_class: str = 'person',
    evaluation_iou_threshold: float = .5,
) -> dict:
    """Return JSON-safe evaluation, withholding ALL accuracy until human review.

    Each image requires image_id, integer width/height, reviewed_by_human,
    annotation_source='human_manual', and ground_truth annotation objects.
    Each annotation uses class_name and normalized bbox. Each prediction also
    requires image_id and confidence. Empty *reviewed* ground truth is a real
    negative image; empty unreviewed ground truth is unknown, never negative.

    Tied prediction confidence preserves caller order. Greedy IoU ties use the
    first annotation in caller order. No input record is changed. Precision and
    recall are None when their denominators are zero; count-form F1 is None
    only when 2TP+FP+FN is zero. Empty-global-GT AP is always undefined (None).
    """
    person_class = _text(person_class, 'person_class')
    iou_threshold = _number(evaluation_iou_threshold, 'evaluation_iou_threshold')
    if not isinstance(confidence_thresholds, Sequence) or isinstance(confidence_thresholds, (str, bytes)) or not confidence_thresholds:
        raise ValueError('confidence_thresholds must be a nonempty sequence')
    thresholds = [_number(value, 'confidence_threshold') for value in confidence_thresholds]
    if len(set(thresholds)) != len(thresholds):
        raise ValueError('Duplicate confidence threshold')
    image_map, ground_truth, missing, issues, reviewed_count, prepared, ignored = _prepare(images, predictions, person_class)
    complete = not missing
    total_gt = sum(map(len, ground_truth.values())) if complete else None
    operating_points = []
    for threshold in thresholds:
        retained = [prediction for prediction in prepared if prediction['confidence'] >= threshold]
        row = dict(confidence_threshold=threshold, iou_threshold=iou_threshold,
                   retained_prediction_count=len(retained), threshold_rejection_count=len(prepared)-len(retained),
                   tp=None, fp=None, fn=None, precision=None, recall=None, f1=None)
        if complete:
            labels = _match(retained, ground_truth, iou_threshold)
            tp = sum(labels)
            fp = len(labels) - tp
            fn = total_gt - tp
            row.update(tp=tp, fp=fp, fn=fn,
                       precision=tp/(tp+fp) if tp+fp else None,
                       recall=tp/(tp+fn) if tp+fn else None,
                       f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None)
        operating_points.append(row)
    ap_rows = [dict(iou_threshold=threshold, ap=_average_precision(_match(prepared, ground_truth, threshold), total_gt) if complete else None)
               for threshold in AP_IOU_THRESHOLDS]
    values = [row['ap'] for row in ap_rows if row['ap'] is not None]
    return dict(
        status='COMPLETE' if complete else 'REVIEW_REQUIRED',
        formal_metrics_available=complete,
        person_class=person_class,
        image_count=len(image_map), human_reviewed_image_count=reviewed_count,
        review_required_image_ids=missing, review_issues=issues,
        ground_truth_person_count=total_gt,
        person_prediction_count=len(prepared), ignored_nonperson_prediction_count=ignored,
        prediction_filter_counts_are_not_accuracy=True,
        thresholds=operating_points,
        ap50=ap_rows[0]['ap'], map50_95=sum(values)/len(values) if values else None,
        ap_by_iou=ap_rows,
        methodology=dict(
            matching='confidence-ranked, per-image, person-class, highest-IoU unmatched ground truth; each GT matched once',
            ap='101-point interpolated precision at recall 0.00, 0.01, ..., 1.00; all supplied person predictions',
            ap_iou_thresholds=list(AP_IOU_THRESHOLDS),
            confidence_ties='stable input prediction order', iou_ties='first annotation order',
            box_convention='normalized xyxy in [0,1], positive area',
            ground_truth='human_manual plus reviewed_by_human=true for every image',
        ),
        limitations=[
            'Person-only AP over supplied prediction records, not a complete COCO benchmark.',
            'AP uses all supplied confidences; upstream detector confidence floors and candidate caps must be disclosed separately.',
            'Unreviewed images are unknown, not negative images; predictions are never ground truth.',
            'No crowd, ignore-region, area-range, or COCO maxDets handling is implemented.',
        ],
    )
