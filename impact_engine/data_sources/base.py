"""
Base interfaces and common classes for the data abstraction layer.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
import pandas as pd
from datetime import datetime
from dataclasses import dataclass


class DataSourceInterface(ABC):
    """Abstract base class defining the contract for all data source implementations."""
    
    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> bool:
        """Establish connection to the data source."""
        pass
    
    @abstractmethod
    def retrieve_business_metrics(self, products: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """Retrieve business metrics for specified products and time range."""
        pass
    
    @abstractmethod
    def validate_connection(self) -> bool:
        """Validate that the data source connection is active and functional."""
        pass
    
    @abstractmethod
    def get_available_metrics(self) -> List[str]:
        """Return list of available metric types supported by this data source."""
        pass


class DataNotFoundError(Exception):
    """Exception raised when no data is found for the specified criteria."""
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