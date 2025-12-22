from .config import ConfigurationError, ConfigurationParser, parse_config_file
from .engine import evaluate_impact
from .metrics import CatalogSimulatorAdapter, MetricsInterface, MetricsManager
from .models import InterruptedTimeSeriesAdapter, Model, ModelsManager

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
