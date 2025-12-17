from .run_impact_analysis import evaluate_impact
from .metrics import MetricsInterface, MetricsNotFoundError, MetricsManager, TimeRange, CatalogSimulatorAdapter
from .models import Model, ModelsManager, InterruptedTimeSeriesAdapter
from .config import ConfigurationParser, ConfigurationError, parse_config_file
"""
Impact Engine - A tool for measuring causal impact of product interventions.
"""

__version__ = "0.1.0"
__author__ = "Impact Engine Team"



__all__ = [
    "evaluate_impact",
    "MetricsInterface",
    "MetricsNotFoundError", 
    "MetricsManager",
    "TimeRange",
    "CatalogSimulatorAdapter",
    "Model",
    "ModelsManager",
    "InterruptedTimeSeriesAdapter",
    "ConfigurationParser",
    "ConfigurationError",
    "parse_config_file",
]