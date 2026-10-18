"""Human-ground-truth-gated evaluation; never an inference or annotation source."""
from .metrics import evaluate_detections, intersection_over_union

__all__ = ['evaluate_detections', 'intersection_over_union']
