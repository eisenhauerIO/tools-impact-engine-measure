"""
Factory functions for creating MetricsManager instances.

This module handles adapter selection based on configuration,
keeping the MetricsManager class simple and focused on coordination.
"""

from typing import Any, Dict, Optional

from artifact_store import JobInfo

from ..core import Registry
from .base import MetricsInterface
from .manager import MetricsManager

# Registry of available metrics adapters - adapters self-register via decorator
METRICS_REGISTRY: Registry[MetricsInterface] = Registry(MetricsInterface, "metrics adapter")


def create_metrics_manager(
    config: Dict[str, Any],
    parent_job: Optional[JobInfo] = None,
) -> MetricsManager:
    """Create a MetricsManager from a parsed config with DATA.SOURCE structure.

    Args:
        config: The full parsed configuration dict (from parse_config_file()).
        parent_job: Optional parent job for artifact management.

    Returns:
        MetricsManager: Configured manager with the appropriate adapter.

    Raises:
        ValueError: If the configured metrics type is not supported.
    """
    source_type = config["DATA"]["SOURCE"]["type"]
    source_config = config["DATA"]["SOURCE"]["CONFIG"]

    # Include ENRICHMENT config if present (it's at DATA.ENRICHMENT, not SOURCE.CONFIG)
    enrichment = config["DATA"].get("ENRICHMENT")
    if enrichment:
        source_config = {**source_config, "ENRICHMENT": enrichment}

    adapter = get_metrics_adapter(source_type)

    return MetricsManager(
        source_config=source_config,
        metrics_source=adapter,
        source_type=source_type,
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


# Import adapters to trigger self-registration via decorators
# These imports must be at the end after METRICS_REGISTRY is defined
from .catalog_simulator import CatalogSimulatorAdapter  # noqa: E402, F401
from .file import FileAdapter  # noqa: E402, F401
