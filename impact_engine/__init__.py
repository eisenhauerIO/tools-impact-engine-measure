from .engine import evaluate_impact
from .metrics import MetricsInterface, MetricsManager, CatalogSimulatorAdapter
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
    "MetricsManager",
    "CatalogSimulatorAdapter",
    "Model",
    "ModelsManager",
    "InterruptedTimeSeriesAdapter",
    "ConfigurationParser",
    "ConfigurationError",
    "parse_config_file",
]