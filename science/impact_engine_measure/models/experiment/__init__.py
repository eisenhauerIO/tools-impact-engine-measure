"""Experiment model for estimating treatment effects via OLS regression.

This subpackage provides an implementation of OLS regression
with R-style formulas via statsmodels for experimental analysis.
"""

from .adapter import ExperimentAdapter

__all__ = [
    "ExperimentAdapter",
]
