"""ArtifactStore Adapter - wraps artifact_store library to StorageInterface."""

from typing import Any, Dict

import pandas as pd
from artifact_store import create_job

from .base import StorageInterface
from .factory import STORAGE_REGISTRY


@STORAGE_REGISTRY.register_decorator("artifact_store")
class ArtifactStoreAdapter(StorageInterface):
    """Wraps the artifact_store library to provide a consistent storage interface.

    The artifact_store library handles Local and S3 backends internally based on
    the storage_url format. This adapter provides a uniform interface while
    delegating actual storage operations to artifact_store.
    """

    def __init__(self):
        """Initialize the ArtifactStoreAdapter."""
        self.job = None
        self.store = None
        self.is_connected = False

    def connect(self, config: Dict[str, Any]) -> bool:
        """Initialize storage with configuration.

        Args:
            config: Dictionary containing:
                - storage_url: Path or URL (e.g., "./data", "s3://bucket/prefix")
                - prefix: Optional job prefix (default: "job-impact-engine")
                - job_id: Optional job ID for resuming existing jobs or custom IDs.
                    If not provided, a unique ID will be auto-generated.

        Returns:
            bool: True if initialization successful, False otherwise.
        """
        storage_url = config.get("storage_url", "./data")
        prefix = config.get("prefix", "job-impact-engine")
        job_id = config.get("job_id", None)

        self.job = create_job(storage_url, prefix=prefix, job_id=job_id)
        self.store = self.job.get_store()
        self.is_connected = True
        return True

    def write_json(self, path: str, data: Dict[str, Any]) -> None:
        """Write JSON data to storage."""
        if not self.is_connected:
            raise ConnectionError("Storage not connected. Call connect() first.")
        self.store.write_json(path, data)

    def write_csv(self, path: str, df: pd.DataFrame) -> None:
        """Write DataFrame to CSV in storage."""
        if not self.is_connected:
            raise ConnectionError("Storage not connected. Call connect() first.")
        self.store.write_csv(path, df)

    def write_yaml(self, path: str, data: Dict[str, Any]) -> None:
        """Write YAML data to storage."""
        if not self.is_connected:
            raise ConnectionError("Storage not connected. Call connect() first.")
        self.store.write_yaml(path, data)

    def write_parquet(self, path: str, df: pd.DataFrame) -> None:
        """Write DataFrame to Parquet in storage."""
        if not self.is_connected:
            raise ConnectionError("Storage not connected. Call connect() first.")
        self.store.write_parquet(path, df)

    def full_path(self, path: str) -> str:
        """Get the full path/URL for a relative path."""
        if not self.is_connected:
            raise ConnectionError("Storage not connected. Call connect() first.")
        return self.store.full_path(path)

    def validate_connection(self) -> bool:
        """Validate that the storage connection is active."""
        return self.is_connected and self.store is not None

    def get_job(self) -> Any:
        """Get the underlying job object for artifact management."""
        return self.job
