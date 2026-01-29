"""
Storage Manager for coordinating storage operations.

Design: Uses dependency injection to receive storage adapter from factory.
This decouples coordination logic from adapter selection, enabling:
- Easy unit testing with mock adapters
- Adapter selection controlled by configuration, not hardcoded
"""

from typing import Any, Dict, Optional

import pandas as pd

from .base import StorageInterface


class StorageManager:
    """Central coordinator for storage management.

    Uses dependency injection - the storage adapter is passed in via constructor,
    making the manager easy to test with mock implementations.
    """

    def __init__(
        self,
        storage_config: Dict[str, Any],
        adapter: StorageInterface,
    ):
        """Initialize the StorageManager with injected storage adapter.

        Args:
            storage_config: Storage configuration (storage_url, prefix, etc.).
            adapter: The storage implementation to use for persistence.
        """
        self.storage_config = storage_config
        self.adapter = adapter

        # Connect the injected adapter
        if not self.adapter.connect(storage_config):
            raise ConnectionError("Failed to connect to storage")

    def write_json(self, path: str, data: Dict[str, Any]) -> None:
        """Write JSON data to storage.

        Args:
            path: Relative path within the storage location.
            data: Dictionary to serialize as JSON.
        """
        self.adapter.write_json(path, data)

    def write_csv(self, path: str, df: pd.DataFrame) -> None:
        """Write DataFrame to CSV in storage.

        Args:
            path: Relative path within the storage location.
            df: DataFrame to write.
        """
        self.adapter.write_csv(path, df)

    def write_yaml(self, path: str, data: Dict[str, Any]) -> None:
        """Write YAML data to storage.

        Args:
            path: Relative path within the storage location.
            data: Dictionary to serialize as YAML.
        """
        self.adapter.write_yaml(path, data)

    def full_path(self, path: str) -> str:
        """Get the full path/URL for a relative path.

        Args:
            path: Relative path within the storage location.

        Returns:
            str: Full path or URL to the resource.
        """
        return self.adapter.full_path(path)

    def get_current_config(self) -> Optional[Dict[str, Any]]:
        """Get the currently loaded configuration."""
        return self.storage_config

    def get_job(self) -> Any:
        """Get the underlying job object for artifact management.

        This is used for creating nested jobs (e.g., in metrics adapters).

        Returns:
            Job object or None if the adapter doesn't support jobs.
        """
        return self.adapter.get_job()
