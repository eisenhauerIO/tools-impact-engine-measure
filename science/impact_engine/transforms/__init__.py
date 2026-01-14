"""
Transforms module for data transformation operations.

This module provides a registry of transform functions that can be
configured via YAML to process data between SOURCE and MODEL.
"""

from .library import aggregate_by_date, aggregate_for_approximation
from .registry import apply_transform, get_transform, register_transform

__all__ = [
    "get_transform",
    "register_transform",
    "apply_transform",
    "aggregate_by_date",
    "aggregate_for_approximation",
]
