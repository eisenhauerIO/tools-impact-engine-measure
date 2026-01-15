"""Metrics layer for the impact_engine package."""

from .base import MetricsInterface
from .catalog_simulator import CatalogSimulatorAdapter
from .factory import (
    create_metrics_manager,
    create_metrics_manager_from_config,
    create_metrics_manager_from_source_config,
)
from .manager import MetricsManager

__all__ = [
    "MetricsManager",
    "MetricsInterface",
    "CatalogSimulatorAdapter",
    "create_metrics_manager",
    "create_metrics_manager_from_config",
    "create_metrics_manager_from_source_config",
]
