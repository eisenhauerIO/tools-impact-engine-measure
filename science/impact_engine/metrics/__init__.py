"""Metrics layer for the impact_engine package."""

from .adapter_catalog_simulator import CatalogSimulatorAdapter
from .base import MetricsInterface
from .factory import create_metrics_manager, create_metrics_manager_from_config
from .manager import MetricsManager

__all__ = [
    "MetricsManager",
    "MetricsInterface",
    "CatalogSimulatorAdapter",
    "create_metrics_manager",
    "create_metrics_manager_from_config",
]
