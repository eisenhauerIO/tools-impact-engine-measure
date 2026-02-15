"""
Factory functions for creating StorageManager instances.

This module handles storage adapter selection based on configuration,
keeping the StorageManager class simple and focused on coordination.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from ..core import Registry
from .base import StorageInterface

if TYPE_CHECKING:
    from .manager import StorageManager

# Registry of available storage adapters - adapters self-register via decorator
STORAGE_REGISTRY: Registry[StorageInterface] = Registry(StorageInterface, "storage")


def create_storage_manager(
    storage_url: str,
    storage_type: str = "artifact_store",
    prefix: str = "job-impact-engine",
    job_id: Optional[str] = None,
) -> "StorageManager":
    """Create a StorageManager with the appropriate storage adapter.

    This factory function:
    1. Selects the appropriate storage adapter based on storage_type
    2. Creates and returns a configured StorageManager

    Args:
        storage_url: Path or URL for storage (e.g., "./data", "s3://bucket/prefix").
        storage_type: Type of storage adapter to use (default: "artifact_store").
        prefix: Job prefix for organizing artifacts (default: "job-impact-engine").
        job_id: Optional job ID for resuming existing jobs or using custom IDs.
            If not provided, a unique ID will be auto-generated.

    Returns:
        StorageManager: Configured manager with the appropriate adapter.

    Raises:
        ValueError: If the configured storage type is not supported.
    """

    storage_config = {
        "storage_url": storage_url,
        "prefix": prefix,
        "job_id": job_id,
    }

    return create_storage_manager_from_config(storage_config, storage_type)


def create_storage_manager_from_config(
    storage_config: Dict[str, Any],
    storage_type: str = "artifact_store",
) -> "StorageManager":
    """Create a StorageManager from a configuration dict.

    Args:
        storage_config: Storage configuration with storage_url and optional prefix.
        storage_type: Type of storage adapter to use.

    Returns:
        StorageManager: Configured manager with the appropriate adapter.

    Raises:
        ValueError: If the configured storage type is not supported.
    """
    from .manager import StorageManager

    adapter = get_storage_adapter(storage_type)

    return StorageManager(
        storage_config=storage_config,
        adapter=adapter,
    )


def get_storage_adapter(storage_type: str) -> StorageInterface:
    """Get an instance of the storage adapter for the given type.

    Args:
        storage_type: The type of storage (e.g., "artifact_store").

    Returns:
        StorageInterface: An instance of the appropriate adapter.

    Raises:
        ValueError: If the storage type is not supported.
    """
    return STORAGE_REGISTRY.get(storage_type)


# Import adapters to trigger self-registration via decorators
# These imports must be at the end after STORAGE_REGISTRY is defined
from .artifact_store_adapter import ArtifactStoreAdapter  # noqa: E402, F401
