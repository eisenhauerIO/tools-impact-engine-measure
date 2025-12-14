from .run_impact_analysis import evaluate_impact
"""
Impact Engine - A tool for measuring causal impact of product interventions.
"""

__version__ = "0.1.0"
__author__ = "Impact Engine Team"

from .core.data_models import (
    ProductIntervention,
    ProductTimeSeries,
    AnalysisResult,
    TimeSeriesPoint,
    CausalEffect,
    ProductMetadata,
    AnalysisDiagnostics,
    ConfidenceInterval,
    StatisticalSignificance,
)

__all__ = [
    "ProductIntervention",
    "ProductTimeSeries", 
    "AnalysisResult",
    "TimeSeriesPoint",
    "CausalEffect",
    "ProductMetadata",
    "AnalysisDiagnostics",
    "ConfidenceInterval",
    "StatisticalSignificance",
    "evaluate_impact",
]