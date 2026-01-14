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
        source_config: Dict[str, Any],
        metrics_source: MetricsInterface,
        parent_job: Optional[JobInfo] = None,
    ):
        """Initialize the MetricsManager with injected metrics source.

        Args:
            source_config: SOURCE.CONFIG configuration block containing date range and settings.
            metrics_source: The metrics implementation to use for data retrieval.
            parent_job: Optional parent job for artifact management.
        """
        self.source_config = source_config
        self.metrics_source = metrics_source
        self.parent_job = parent_job

        # Validate the source config
        self._validate_source_config(source_config)

        # Connect the injected metrics source
        connection_config = self._build_connection_config()
        if not self.metrics_source.connect(connection_config):
            raise ConnectionError("Failed to connect to metrics source")

    def _validate_source_config(self, source_config: Dict[str, Any]) -> None:
        """Validate SOURCE.CONFIG configuration block."""
        required_fields = ["START_DATE", "END_DATE"]
        for field in required_fields:
            if field not in source_config:
                raise ValueError(f"Missing required field '{field}' in SOURCE.CONFIG configuration")

        # Validate date format
        try:
            start_date = datetime.strptime(source_config["START_DATE"], "%Y-%m-%d")
            end_date = datetime.strptime(source_config["END_DATE"], "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(
                f"Invalid date format in SOURCE.CONFIG configuration. Expected YYYY-MM-DD: {e}"
            )

        # Validate date consistency
        if start_date > end_date:
            raise ValueError(
                "START_DATE must be before or equal to END_DATE in SOURCE.CONFIG configuration"
            )

    def _build_connection_config(self) -> Dict[str, Any]:
        """Build connection configuration from SOURCE.CONFIG.

        Note: Primary defaults are in config_defaults.yaml. These fallbacks
        ensure direct manager usage (without process_config) still works.
        """
        config = {
            "mode": self.source_config.get("MODE", "rule"),
            "seed": self.source_config.get("SEED", 42),
            "parent_job": self.parent_job,
        }

        # Pass enrichment config if present
        if "ENRICHMENT" in self.source_config:
            config["enrichment"] = self.source_config["ENRICHMENT"]

        return config

    def retrieve_metrics(self, products: pd.DataFrame) -> pd.DataFrame:
        """Retrieve business metrics for specified products using SOURCE.CONFIG date range."""
        if products is None or len(products) == 0:
            raise ValueError("Products DataFrame cannot be empty")

        # Get date range from SOURCE.CONFIG
        start_date = self.source_config["START_DATE"]
        end_date = self.source_config["END_DATE"]

        return self.metrics_source.retrieve_business_metrics(
            products=products, start_date=start_date, end_date=end_date
        )

    def get_current_config(self) -> Optional[Dict[str, Any]]:
        """Get the currently loaded configuration."""
        return self.source_config
