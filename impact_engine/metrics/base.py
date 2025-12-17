"""
Base interfaces and common classes for the metrics layer.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
import pandas as pd
from datetime import datetime
from dataclasses import dataclass


class MetricsInterface(ABC):
    """Abstract base class defining the contract for all metrics implementations."""
    
    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> bool:
        """Establish connection to the metrics source."""
        pass
    
    @abstractmethod
    def retrieve_business_metrics(self, products: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
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
    



class MetricsNotFoundError(Exception):
    """Exception raised when no metrics are found for the specified criteria."""
    pass


@dataclass
class TimeRange:
    """Data class representing a time range for metrics retrieval."""
    start_date: datetime
    end_date: datetime
    
    def validate(self) -> bool:
        """Validate that the time range is logically consistent."""
        return self.start_date <= self.end_date
    
    @classmethod
    def from_strings(cls, start_date_str: str, end_date_str: str) -> 'TimeRange':
        """Create TimeRange from string dates."""
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"Invalid date format. Expected YYYY-MM-DD: {e}")
        
        time_range = cls(start_date, end_date)
        if not time_range.validate():
            raise ValueError(f"Invalid time range: start_date ({start_date_str}) must be <= end_date ({end_date_str})")
        
        return time_range