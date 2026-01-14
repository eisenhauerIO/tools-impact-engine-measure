"""Models layer for the impact_engine package."""

from .base import Model
from .factory import create_models_manager, create_models_manager_from_config
from .interrupted_time_series import InterruptedTimeSeriesAdapter
from .manager import ModelsManager
from .metrics_approximation import MetricsApproximationAdapter

__all__ = [
    "Model",
    "ModelsManager",
    "InterruptedTimeSeriesAdapter",
    "MetricsApproximationAdapter",
    "create_models_manager",
    "create_models_manager_from_config",
]
