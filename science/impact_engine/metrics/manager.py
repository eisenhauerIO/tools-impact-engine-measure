"""
Metrics Manager for coordinating metrics operations.
"""

from typing import Any, Dict, Optional

import pandas as pd
from artifact_store import JobInfo

from .base import MetricsInterface


class MetricsManager:
    """Central coordinator for metrics management.

    Uses dependency injection - the metrics source is passed in via constructor,
    making the manager easy to test with mock implementations.

    Note: source_config is expected to be pre-validated via process_config().
    """

    def __init__(
        self,
        source_config: Dict[str, Any],
        metrics_source: MetricsInterface,
        parent_job: Optional[JobInfo] = None,
    ):
        """Initialize the MetricsManager with injected metrics source.

        Args:
            source_config: SOURCE.CONFIG configuration block (pre-validated, with defaults merged).
            metrics_source: The metrics implementation to use for data retrieval.
            parent_job: Optional parent job for artifact management.
        """
        self.source_config = source_config
        self.metrics_source = metrics_source
        self.parent_job = parent_job

        # Connect the injected metrics source
        connection_config = self._build_connection_config()
        if not self.metrics_source.connect(connection_config):
            raise ConnectionError("Failed to connect to metrics source")

    def _build_connection_config(self) -> Dict[str, Any]:
        """Build connection configuration from SOURCE.CONFIG.

        Config is pre-validated with defaults merged, so direct access is safe.
        """
        config = {
            "mode": self.source_config["mode"],
            "seed": self.source_config["seed"],
            "parent_job": self.parent_job,
        }

        # Pass enrichment config if present (ENRICHMENT is optional)
        if "ENRICHMENT" in self.source_config:
            config["enrichment"] = self.source_config["ENRICHMENT"]

        return config

    def retrieve_metrics(self, products: pd.DataFrame) -> pd.DataFrame:
        """Retrieve business metrics for specified products using SOURCE.CONFIG date range."""
        if products is None or len(products) == 0:
            raise ValueError("Products DataFrame cannot be empty")

        # Get date range from SOURCE.CONFIG
        start_date = self.source_config["start_date"]
        end_date = self.source_config["end_date"]

        return self.metrics_source.retrieve_business_metrics(
            products=products, start_date=start_date, end_date=end_date
        )

    def get_current_config(self) -> Optional[Dict[str, Any]]:
        """Get the currently loaded configuration."""
        return self.source_config
