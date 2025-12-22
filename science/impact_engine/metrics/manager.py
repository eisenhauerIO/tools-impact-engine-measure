"""
Metrics Manager for coordinating metrics operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from artifact_store import JobInfo

from ..config import ConfigurationParser
from .adapter_catalog_simulator import CatalogSimulatorAdapter
from .base import MetricsInterface


class MetricsManager:
    """Central coordinator for metrics management."""

    def __init__(self, data_config: Dict[str, Any], parent_job: Optional[JobInfo] = None):
        """Initialize the MetricsManager with DATA configuration block."""
        self.metrics_registry: Dict[str, type] = {}
        self.data_config = data_config
        self.parent_job = parent_job
        self._register_builtin_metrics()

        # Validate the data config
        self._validate_data_config(data_config)

    @classmethod
    def from_config_file(
        cls, config_path: str, parent_job: Optional[JobInfo] = None
    ) -> "MetricsManager":
        """Create MetricsManager from config file, extracting DATA block."""
        config_parser = ConfigurationParser()
        full_config = config_parser.parse_config(config_path)
        return cls(full_config["DATA"], parent_job=parent_job)

    def _register_builtin_metrics(self) -> None:
        """Register built-in metrics implementations."""
        self.register_metrics("simulator", CatalogSimulatorAdapter)

    def register_metrics(self, source_type: str, source_class: type) -> None:
        """Register a new metrics implementation."""
        if not issubclass(source_class, MetricsInterface):
            raise ValueError(
                f"Metrics class {source_class.__name__} must implement MetricsInterface"
            )
        self.metrics_registry[source_type] = source_class

    def _validate_data_config(self, data_config: Dict[str, Any]) -> None:
        """Validate DATA configuration block."""
        required_fields = ["TYPE", "START_DATE", "END_DATE"]
        for field in required_fields:
            if field not in data_config:
                raise ValueError(f"Missing required field '{field}' in DATA configuration")

        # Validate date format
        try:
            start_date = datetime.strptime(data_config["START_DATE"], "%Y-%m-%d")
            end_date = datetime.strptime(data_config["END_DATE"], "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"Invalid date format in DATA configuration. Expected YYYY-MM-DD: {e}")

        # Validate date consistency
        if start_date > end_date:
            raise ValueError("START_DATE must be before or equal to END_DATE in DATA configuration")

    def get_metrics_source(self, source_type: Optional[str] = None) -> MetricsInterface:
        """Get metrics implementation based on configuration or specified type."""
        if source_type is None:
            source_type = self.data_config["TYPE"]

        if source_type not in self.metrics_registry:
            raise ValueError(
                f"Unknown metrics type '{source_type}'. Available: {list(self.metrics_registry.keys())}"
            )

        metrics_source = self.metrics_registry[source_type]()

        # Build connection config from DATA configuration
        connection_config = {
            "mode": self.data_config.get("MODE", "rule"),
            "seed": self.data_config.get("SEED", 42),
            "parent_job": self.parent_job,
        }

        # Pass enrichment config if present
        if "ENRICHMENT" in self.data_config:
            connection_config["enrichment"] = self.data_config["ENRICHMENT"]

        if not metrics_source.connect(connection_config):
            raise ConnectionError(f"Failed to connect to {source_type} metrics source")

        return metrics_source

    def retrieve_metrics(self, products: pd.DataFrame) -> pd.DataFrame:
        """Retrieve business metrics for specified products using DATA configuration date range."""
        if products is None or len(products) == 0:
            raise ValueError("Products DataFrame cannot be empty")

        # Get date range from DATA configuration
        start_date = self.data_config["START_DATE"]
        end_date = self.data_config["END_DATE"]

        # Get metrics source
        metrics_source = self.get_metrics_source()

        return metrics_source.retrieve_business_metrics(
            products=products, start_date=start_date, end_date=end_date
        )

    def get_available_metrics(self) -> List[str]:
        """Get list of available metrics types."""
        return list(self.metrics_registry.keys())

    def get_current_config(self) -> Optional[Dict[str, Any]]:
        """Get the currently loaded configuration."""
        return self.data_config
