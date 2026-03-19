"""Base interfaces and common classes for the metrics layer."""

from abc import ABC, abstractmethod
from typing import Any, Dict

import pandas as pd


class MetricsInterface(ABC):
    """Abstract base class defining the contract for all metrics implementations.

    Required methods (must override):
        - connect: Initialize adapter with configuration
        - retrieve_business_metrics: Fetch metrics data

    Optional methods (have sensible defaults):
        - validate_connection: Check if connection is active
        - transform_outbound: Transform data to external format
        - transform_inbound: Transform data from external format
    """

    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> bool:
        """Establish connection to the metrics source."""
        pass

    @abstractmethod
    def retrieve_business_metrics(self, products: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
        """Retrieve business metrics for specified products and time range.

        Parameters
        ----------
        products : pd.DataFrame
            DataFrame with product identifiers and characteristics.
        start_date : str
            Start date in YYYY-MM-DD format.
        end_date : str
            End date in YYYY-MM-DD format.

        Returns
        -------
        pd.DataFrame
            DataFrame with business metrics for the specified products.
        """
        pass

    def validate_connection(self) -> bool:
        """Validate that the metrics source connection is active and functional.

        Default implementation returns True. Override for custom validation.

        Returns
        -------
        bool
            True if connection is valid, False otherwise.
        """
        return True

    def transform_outbound(self, products: pd.DataFrame, start_date: str, end_date: str) -> Dict[str, Any]:
        """Transform impact engine format to external system format.

        Default implementation is pass-through.
        Override for adapters that need data transformation.

        Parameters
        ----------
        products : pd.DataFrame
            DataFrame with product identifiers and characteristics.
        start_date : str
            Start date in YYYY-MM-DD format.
        end_date : str
            End date in YYYY-MM-DD format.

        Returns
        -------
        dict
            Dictionary with parameters formatted for the external system.
        """
        return {"products": products, "start_date": start_date, "end_date": end_date}

    def transform_inbound(self, external_data: Any) -> pd.DataFrame:
        """Transform external system response to impact engine format.

        Default implementation returns data as-is if DataFrame, otherwise raises.
        Override for adapters that need result transformation.

        Parameters
        ----------
        external_data : Any
            Raw data from the external system.

        Returns
        -------
        pd.DataFrame
            DataFrame with standardized business metrics format.
        """
        if isinstance(external_data, pd.DataFrame):
            return external_data
        raise ValueError(f"Expected DataFrame, got {type(external_data).__name__}")
