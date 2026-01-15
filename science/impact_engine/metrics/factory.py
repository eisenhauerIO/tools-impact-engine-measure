"""
Factory functions for creating MetricsManager instances.

This module handles adapter selection based on configuration,
keeping the MetricsManager class simple and focused on coordination.
"""

from typing import Any, Dict, Optional

from artifact_store import JobInfo

from ..config import get_source_config, get_source_type, parse_config_file
from ..core import Registry
from .base import MetricsInterface
from .catalog_simulator import CatalogSimulatorAdapter
from .manager import MetricsManager

# Registry of available metrics adapters
METRICS_REGISTRY: Registry[MetricsInterface] = Registry(MetricsInterface, "metrics adapter")
METRICS_REGISTRY.register("simulator", CatalogSimulatorAdapter)


def create_metrics_manager(
    config_path: str,
    parent_job: Optional[JobInfo] = None,
) -> MetricsManager:
    """Create a MetricsManager from a configuration file.

    This factory function:
    1. Parses the configuration file
    2. Selects the appropriate metrics adapter based on DATA.SOURCE.TYPE
    3. Creates and returns a configured MetricsManager

    Args:
        config_path: Path to the configuration file (YAML or JSON).
        parent_job: Optional parent job for artifact management.

    Returns:
        MetricsManager: Configured manager with the appropriate adapter.

    Raises:
        ValueError: If the configured metrics type is not supported.
        FileNotFoundError: If the configuration file doesn't exist.
    """
    config = parse_config_file(config_path)
    return create_metrics_manager_from_source_config(config, parent_job)


def create_metrics_manager_from_source_config(
    config: Dict[str, Any],
    parent_job: Optional[JobInfo] = None,
) -> MetricsManager:
    """Create a MetricsManager from a parsed config with DATA.SOURCE structure.

    Args:
        config: The full parsed configuration dict.
        parent_job: Optional parent job for artifact management.

    Returns:
        MetricsManager: Configured manager with the appropriate adapter.

    Raises:
        ValueError: If the configured metrics type is not supported.
    """
    source_type = get_source_type(config)
    source_config = get_source_config(config)

    # Include ENRICHMENT config if present (it's at DATA.ENRICHMENT, not SOURCE.CONFIG)
    enrichment = config["DATA"].get("ENRICHMENT")
    if enrichment:
        source_config = {**source_config, "ENRICHMENT": enrichment}

    adapter = get_metrics_adapter(source_type)

    return MetricsManager(
        source_config=source_config,
        metrics_source=adapter,
        parent_job=parent_job,
    )


def create_metrics_manager_from_config(
    data_config: Dict[str, Any],
    parent_job: Optional[JobInfo] = None,
) -> MetricsManager:
    """Create a MetricsManager from a SOURCE.CONFIG configuration dict.

    Args:
        data_config: The SOURCE.CONFIG configuration block.
        parent_job: Optional parent job for artifact management.

    Returns:
        MetricsManager: Configured manager with the appropriate adapter.

    Raises:
        ValueError: If the configured metrics type is not supported.
    """
    # This function now expects just the SOURCE.CONFIG part
    # Use default "simulator" type if TYPE not in config
    metrics_type = data_config.get("TYPE", "simulator")

    adapter = get_metrics_adapter(metrics_type)

    return MetricsManager(
        source_config=data_config,
        metrics_source=adapter,
        parent_job=parent_job,
    )


def get_metrics_adapter(metrics_type: str) -> MetricsInterface:
    """Get an instance of the metrics adapter for the given type.

    Args:
        metrics_type: The type of metrics adapter (e.g., "simulator").

    Returns:
        MetricsInterface: An instance of the appropriate adapter.

    Raises:
        ValueError: If the metrics type is not supported.
    """
    return METRICS_REGISTRY.get(metrics_type)
