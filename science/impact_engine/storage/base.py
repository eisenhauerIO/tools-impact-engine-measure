"""
Base interfaces and common classes for the storage layer.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

import pandas as pd


class StorageInterface(ABC):
    """Abstract base class defining the contract for all storage implementations.

    Required methods (must override):
        - connect: Initialize adapter with configuration
        - write_json: Write JSON data to storage
        - write_csv: Write DataFrame to CSV
        - write_yaml: Write YAML data to storage
        - write_parquet: Write DataFrame to Parquet
        - full_path: Get full path/URL for a relative path

    Optional methods (have sensible defaults):
        - validate_connection: Check if connection is active
    """

    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> bool:
        """Initialize storage with configuration.

        Args:
            config: Dictionary containing storage configuration (e.g., storage_url, prefix).

        Returns:
            bool: True if initialization successful, False otherwise.
        """
        pass

    @abstractmethod
    def write_json(self, path: str, data: Dict[str, Any]) -> None:
        """Write JSON data to storage.

        Args:
            path: Relative path within the storage location.
            data: Dictionary to serialize as JSON.
        """
        pass

    @abstractmethod
    def write_csv(self, path: str, df: pd.DataFrame) -> None:
        """Write DataFrame to CSV in storage.

        Args:
            path: Relative path within the storage location.
            df: DataFrame to write.
        """
        pass

    @abstractmethod
    def write_yaml(self, path: str, data: Dict[str, Any]) -> None:
        """Write YAML data to storage.

        Args:
            path: Relative path within the storage location.
            data: Dictionary to serialize as YAML.
        """
        pass

    @abstractmethod
    def write_parquet(self, path: str, df: pd.DataFrame) -> None:
        """Write DataFrame to Parquet in storage.

        Args:
            path: Relative path within the storage location.
            df: DataFrame to write.
        """
        pass

    @abstractmethod
    def full_path(self, path: str) -> str:
        """Get the full path/URL for a relative path.

        Args:
            path: Relative path within the storage location.

        Returns:
            str: Full path or URL to the resource.
        """
        pass

    def validate_connection(self) -> bool:
        """Validate that the storage connection is active and functional.

        Default implementation returns True. Override for custom validation.

        Returns:
            bool: True if connection is valid, False otherwise.
        """
        return True

    def get_job(self) -> Any:
        """Get the underlying job object for artifact management.

        This is used for creating nested jobs or accessing job metadata.
        Default implementation returns None. Override for adapters that
        support job-based artifact management.

        Returns:
            Job object or None if not applicable.
        """
        return None
