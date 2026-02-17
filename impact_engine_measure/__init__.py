"""
Impact Engine - A tool for measuring causal impact of product interventions.
"""

from .config import ConfigurationError, ConfigurationParser, parse_config_file
from .engine import evaluate_impact
from .metrics import (
    METRICS_REGISTRY,
    MetricsInterface,
    MetricsManager,
    create_metrics_manager,
)
from .models import MODEL_REGISTRY, ModelInterface, ModelsManager, create_models_manager
from .results import MeasureJobResult, load_results

__version__ = "0.1.0"
__author__ = "eisenhauer.io"


__all__ = [
    "evaluate_impact",
    "load_results",
    "MeasureJobResult",
    "MetricsInterface",
    "MetricsManager",
    "METRICS_REGISTRY",
    "create_metrics_manager",
    "ModelInterface",
    "ModelsManager",
    "MODEL_REGISTRY",
    "create_models_manager",
    "ConfigurationParser",
    "ConfigurationError",
    "parse_config_file",
]
