"""Metrics-based impact approximation model.

This subpackage provides a general framework for approximating treatment impact
based on changes in measurable metrics (e.g., quality scores) and their
relationship to business outcomes.
"""

from .adapter import MetricsApproximationAdapter
from .response_registry import register_response_function
from .transforms import aggregate_for_approximation

__all__ = [
    "MetricsApproximationAdapter",
    "aggregate_for_approximation",
    "register_response_function",
]
