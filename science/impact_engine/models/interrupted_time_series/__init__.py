"""Interrupted Time Series model for causal impact estimation.

This subpackage provides an implementation of Interrupted Time Series (ITS)
analysis using SARIMAX from statsmodels to estimate causal impact of
interventions on time series data.
"""

from .adapter import InterruptedTimeSeriesAdapter

__all__ = [
    "InterruptedTimeSeriesAdapter",
]
