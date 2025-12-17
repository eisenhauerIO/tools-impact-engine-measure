"""
Data Source Manager for coordinating data source operations.
"""

import pandas as pd
from typing import Dict, List, Any, Optional

from .base import DataSourceInterface, TimeRange
from .simulator import SimulatorDataSource
from ..config import ConfigurationParser


class DataSourceManager:
    """Central coordinator for data source management."""
    
    def __init__(self):
        """Initialize the DataSourceManager."""
        self.config_parser = ConfigurationParser()
        self.data_source_registry: Dict[str, type] = {}
        self.current_config: Optional[Dict[str, Any]] = None
        self._register_builtin_data_sources()
    
    def _register_builtin_data_sources(self) -> None:
        """Register built-in data source implementations."""
        self.register_data_source("simulator", SimulatorDataSource)
    
    def register_data_source(self, source_type: str, source_class: type) -> None:
        """Register a new data source implementation."""
        if not issubclass(source_class, DataSourceInterface):
            raise ValueError(f"Data source class {source_class.__name__} must implement DataSourceInterface")
        self.data_source_registry[source_type] = source_class
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load and validate configuration from file."""
        self.current_config = self.config_parser.parse_config(config_path)
        return self.current_config
    
    def get_data_source(self, source_type: Optional[str] = None) -> DataSourceInterface:
        """Get data source implementation based on configuration or specified type."""
        if source_type is None:
            if self.current_config is None:
                raise ValueError("No configuration loaded. Call load_config() first or provide source_type.")
            source_type = self.current_config["data_source"]["type"]
        
        if source_type not in self.data_source_registry:
            raise ValueError(f"Unknown data source type '{source_type}'. Available: {list(self.data_source_registry.keys())}")
        
        data_source = self.data_source_registry[source_type]()
        
        if self.current_config is not None:
            connection_config = self.current_config["data_source"]["connection"]
            if not data_source.connect(connection_config):
                raise ConnectionError(f"Failed to connect to {source_type} data source")
        
        return data_source
    
    def retrieve_metrics(
        self, 
        products: List[str], 
        time_range: Optional[TimeRange] = None,
        data_source: Optional[DataSourceInterface] = None
    ) -> pd.DataFrame:
        """Retrieve business metrics for specified products and time range."""
        if not products:
            raise ValueError("Products list cannot be empty")
        
        if time_range is None:
            if self.current_config is None:
                raise ValueError("No configuration loaded. Provide time_range or call load_config() first.")
            time_config = self.current_config["time_range"]
            time_range = TimeRange.from_strings(time_config["start_date"], time_config["end_date"])
        
        if data_source is None:
            data_source = self.get_data_source()
        
        return data_source.retrieve_business_metrics(
            products=products,
            start_date=time_range.start_date.strftime("%Y-%m-%d"),
            end_date=time_range.end_date.strftime("%Y-%m-%d")
        )
    
    def get_available_data_sources(self) -> List[str]:
        """Get list of available data source types."""
        return list(self.data_source_registry.keys())
    
    def get_current_config(self) -> Optional[Dict[str, Any]]:
        """Get the currently loaded configuration."""
        return self.current_config