"""Nearest neighbour matching for treatment effect estimation.

This subpackage provides an implementation of nearest neighbour matching
that pairs treated and control units on observed covariates to estimate
ATT, ATC, and ATE.
"""

from .adapter import NearestNeighbourMatchingAdapter

__all__ = [
    "NearestNeighbourMatchingAdapter",
]
