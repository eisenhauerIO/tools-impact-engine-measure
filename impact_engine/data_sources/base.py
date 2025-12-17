"""
Base interfaces and common classes for the data abstraction layer.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
import pandas as pd
from datetime import datetime
from dataclasses import dataclass


class DataSourceInterface(ABC):
    """
    Abstract base class defining the contract for all data source implementations.
    
    This interface ensures consistent behavior across different data sources
    (simulators, company databases, APIs) while allowing for source-specific
    implementations of connection, data retrieval, and validation logic.
    """
    
    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> bool:
        """
        Establish connection to the data source.
        
        Args:
            config: Dictionary containing connection parameters specific to the
                   data source type. May include credentials, endpoints, timeouts,
                   and other connection-specific settings.
        
        Returns:
            bool: True if connection was established successfully, False otherwise.
        
        Raises:
            ConnectionError: If connection cannot be established due to network,
                           authentication, or configuration issues.
            ValueError: If required configuration parameters are missing or invalid.
        """
        pass
    
    @abstractmethod
    def retrieve_business_metrics(
        self, 
        products: List[str], 
        start_date: str, 
        end_date: str
    ) -> pd.DataFrame:
        """
        Retrieve business metrics for specified products and time range.
        
        This method returns a standardized DataFrame containing business metrics
        for the requested products within the specified date range. The output
        format is consistent across all data source implementations.
        
        Args:
            products: List of product identifiers to retrieve metrics for.
                     Format depends on data source (e.g., SKUs, product IDs).
            start_date: Start date for metrics retrieval in ISO format (YYYY-MM-DD).
            end_date: End date for metrics retrieval in ISO format (YYYY-MM-DD).
        
        Returns:
            pd.DataFrame: Standardized business metrics with the following schema:
                - asin (str): Unique product identifier
                - name (str): Product name
                - category (str): Product category
                - price (float): Product price
                - date (datetime): Date for the metrics
                - sales_volume (int): Units sold on this date
                - revenue (float): Revenue generated on this date
                - inventory_level (int): Inventory count on this date
                - customer_engagement (float): Engagement score (0-1)
                - data_source (str): Source identifier
                - retrieval_timestamp (datetime): When data was retrieved
        
        Raises:
            ValueError: If date range is invalid (start_date > end_date) or
                       date format is incorrect.
            ConnectionError: If data source is not accessible or connection failed.
            DataNotFoundError: If no data exists for specified products/time range.
        """
        pass
    
    @abstractmethod
    def validate_connection(self) -> bool:
        """
        Validate that the data source connection is active and functional.
        
        This method performs a lightweight check to ensure the data source
        is accessible and responding correctly. It should be called before
        attempting data retrieval operations.
        
        Returns:
            bool: True if connection is valid and data source is accessible,
                 False otherwise.
        
        Raises:
            ConnectionError: If validation fails due to network or service issues.
        """
        pass
    
    @abstractmethod
    def get_available_metrics(self) -> List[str]:
        """
        Return list of available metric types supported by this data source.
        
        This method provides introspection capabilities to determine what
        types of business metrics are available from the data source.
        
        Returns:
            List[str]: List of available metric names (e.g., 'sales_volume',
                      'revenue', 'inventory_level', 'customer_engagement').
        
        Raises:
            ConnectionError: If unable to query data source for available metrics.
        """
        pass


class DataNotFoundError(Exception):
    """
    Exception raised when no data is found for the specified criteria.
    
    This exception is used to distinguish between connection errors and
    cases where the data source is accessible but contains no data
    matching the requested products and time range.
    """
    pass


@dataclass
class TimeRange:
    """
    Data class representing a time range for metrics retrieval.
    
    Provides validation and helper methods for date range operations.
    """
    start_date: datetime
    end_date: datetime
    
    def validate(self) -> bool:
        """
        Validate that the time range is logically consistent.
        
        Returns:
            bool: True if start_date <= end_date, False otherwise
        """
        return self.start_date <= self.end_date
    
    @classmethod
    def from_strings(cls, start_date_str: str, end_date_str: str) -> 'TimeRange':
        """
        Create TimeRange from string dates.
        
        Args:
            start_date_str: Start date in YYYY-MM-DD format
            end_date_str: End date in YYYY-MM-DD format
        
        Returns:
            TimeRange: New TimeRange instance
        
        Raises:
            ValueError: If date format is invalid or range is invalid
        """
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"Invalid date format. Expected YYYY-MM-DD: {e}")
        
        time_range = cls(start_date, end_date)
        if not time_range.validate():
            raise ValueError(f"Invalid time range: start_date ({start_date_str}) must be <= end_date ({end_date_str})")
        
        return time_range