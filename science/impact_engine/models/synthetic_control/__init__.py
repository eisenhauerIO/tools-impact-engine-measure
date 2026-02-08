"""Synthetic Control model for causal impact estimation.

This subpackage provides an implementation of the Synthetic Control method
using CausalPy to estimate causal impact by constructing a weighted
combination of control units as a counterfactual.
"""

from .adapter import SyntheticControlAdapter
from .transforms import pivot_to_wide, prepare_for_synthetic_control

__all__ = [
    "SyntheticControlAdapter",
    "pivot_to_wide",
    "prepare_for_synthetic_control",
]
