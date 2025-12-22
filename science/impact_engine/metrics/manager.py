"""
Metrics Manager for coordinating metrics operations.
"""

from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd
from artifact_store import JobInfo

from .base import MetricsInterface


class MetricsManager:
    """Central coordinator for metrics management.

    Uses dependency injection - the metrics source is passed in via constructor,
    making the manager easy to test with mock implementations.
    """

    def __init__(
        self,
        data_config: Dict[str, Any],
        metrics_source: MetricsInterface,
        parent_job: Optional[JobInfo] = None,
    ):
        """Initialize the MetricsManager with injected metrics source.

        Args:
            data_config: DATA configuration block containing date range and settings.
            metrics_source: The metrics implementation to use for data retrieval.
            parent_job: Optional parent job for artifact management.
        """
        self.data_config = data_config
        self.metrics_source = metrics_source
        self.parent_job = parent_job

        # Validate the data config
        self._validate_data_config(data_config)

        # Connect the injected metrics source
        connection_config = self._build_connection_config()
        if not self.metrics_source.connect(connection_config):
            raise ConnectionError("Failed to connect to metrics source")

    def _validate_data_config(self, data_config: Dict[str, Any]) -> None:
        """Validate DATA configuration block."""
        required_fields = ["START_DATE", "END_DATE"]
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

    def _build_connection_config(self) -> Dict[str, Any]:
        """Build connection configuration from DATA config."""
        config = {
            "mode": self.data_config.get("MODE", "rule"),
            "seed": self.data_config.get("SEED", 42),
            "parent_job": self.parent_job,
        }

        # Pass enrichment config if present
        if "ENRICHMENT" in self.data_config:
            config["enrichment"] = self.data_config["ENRICHMENT"]

        return config

    def retrieve_metrics(self, products: pd.DataFrame) -> pd.DataFrame:
        """Retrieve business metrics for specified products using DATA configuration date range."""
        if products is None or len(products) == 0:
            raise ValueError("Products DataFrame cannot be empty")

        # Get date range from DATA configuration
        start_date = self.data_config["START_DATE"]
        end_date = self.data_config["END_DATE"]

        return self.metrics_source.retrieve_business_metrics(
            products=products, start_date=start_date, end_date=end_date
        )

    def get_current_config(self) -> Optional[Dict[str, Any]]:
        """Get the currently loaded configuration."""
        return self.data_config
