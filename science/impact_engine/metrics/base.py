"""
Base interfaces and common classes for the metrics layer.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

import pandas as pd


class MetricsInterface(ABC):
    """Abstract base class defining the contract for all metrics implementations."""

    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> bool:
        """Establish connection to the metrics source."""
        pass

    @abstractmethod
    def retrieve_business_metrics(
        self, products: pd.DataFrame, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """Retrieve business metrics for specified products and time range.

        Args:
            products: DataFrame with product identifiers and characteristics
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            DataFrame with business metrics for the specified products
        """
        pass

    @abstractmethod
    def validate_connection(self) -> bool:
        """Validate that the metrics source connection is active and functional."""
        pass

    @abstractmethod
    def transform_outbound(
        self, products: pd.DataFrame, start_date: str, end_date: str
    ) -> Dict[str, Any]:
        """Transform impact engine format to external system format.

        Args:
            products: DataFrame with product identifiers and characteristics
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            Dictionary with parameters formatted for the external system
        """
        pass

    @abstractmethod
    def transform_inbound(self, external_data: Any) -> pd.DataFrame:
        """Transform external system response to impact engine format.

        Args:
            external_data: Raw data from the external system

        Returns:
            DataFrame with standardized business metrics format
        """
        pass
