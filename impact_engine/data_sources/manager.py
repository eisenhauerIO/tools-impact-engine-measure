"""
Data Source Manager for coordinating data source operations.
"""

import pandas as pd
import logging
import time
from typing import Dict, List, Any, Optional

from .base import DataSourceInterface, TimeRange, DataNotFoundError
from .simulator import SimulatorDataSource
from ..config import ConfigurationParser, ConfigurationError


class DataSourceManager:
    """
    Central coordinator for data source management and configuration.
    
    This class provides the main interface for the data abstraction layer,
    handling configuration loading, data source selection, and coordinating
    data retrieval operations across different data source implementations.
    
    Supports direct registration of external data sources via the register_data_source method.
    """
    
    def __init__(self, enable_debug_logging: bool = False):
        """
        Initialize the DataSourceManager with empty registry and configuration.
        
        Args:
            enable_debug_logging: If True, enables detailed execution traces for debugging
        """
        self.logger = logging.getLogger(__name__)
        self.config_parser = ConfigurationParser()
        self.data_source_registry: Dict[str, type] = {}
        self.current_config: Optional[Dict[str, Any]] = None
        self.current_data_source: Optional[DataSourceInterface] = None
        self.debug_logging = enable_debug_logging
        
        # Performance tracking
        self.operation_stats = {
            'config_loads': 0,
            'data_retrievals': 0,
            'connection_attempts': 0,
            'total_retrieval_time': 0.0,
            'failed_operations': 0
        }
        
        if self.debug_logging:
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug("DataSourceManager initialized with debug logging enabled")
        
        # Register built-in data source types
        self._register_builtin_data_sources()
    
    def _register_builtin_data_sources(self) -> None:
        """Register built-in data source implementations."""
        # Register the simulator data source
        self.register_data_source("simulator", SimulatorDataSource)
    
    def register_data_source(self, source_type: str, source_class: type) -> None:
        """
        Register a new data source implementation for dynamic registration.
        
        This is the main API for external data source registration. Users can
        create their own data source implementations and register them here.
        
        Args:
            source_type: String identifier for the data source type (e.g., "salesforce", "postgres")
            source_class: Class implementing DataSourceInterface
        
        Raises:
            ValueError: If source_class doesn't implement DataSourceInterface
        
        Example:
            # External data source registration
            from my_package.salesforce import SalesforceDataSource
            
            manager = DataSourceManager()
            manager.register_data_source("salesforce", SalesforceDataSource)
            
            # Now can use "salesforce" as data source type in configuration
        """
        try:
            if self.debug_logging:
                self.logger.debug(f"Attempting to register data source type '{source_type}' with class {source_class.__name__}")
            
            if not issubclass(source_class, DataSourceInterface):
                error_msg = f"Data source class {source_class.__name__} must implement DataSourceInterface"
                self.logger.error(f"Registration failed for '{source_type}': {error_msg}")
                raise ValueError(error_msg)
            
            self.data_source_registry[source_type] = source_class
            self.logger.info(f"Successfully registered data source type '{source_type}' with class {source_class.__name__}")
            
            if self.debug_logging:
                self.logger.debug(f"Registry now contains {len(self.data_source_registry)} data source types: {list(self.data_source_registry.keys())}")
                
        except Exception as e:
            self.logger.error(f"Unexpected error during data source registration for '{source_type}': {e}")
            self.operation_stats['failed_operations'] += 1
            raise
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load and validate configuration from file.
        
        Args:
            config_path: Path to the configuration file (JSON or YAML)
        
        Returns:
            Dict[str, Any]: Parsed and validated configuration
        
        Raises:
            ConfigurationError: If configuration parsing or validation fails
            FileNotFoundError: If configuration file does not exist
        """
        start_time = time.time()
        
        try:
            if self.debug_logging:
                self.logger.debug(f"Starting configuration load from {config_path}")
            
            self.current_config = self.config_parser.parse_config(config_path)
            
            load_time = time.time() - start_time
            self.operation_stats['config_loads'] += 1
            
            self.logger.info(f"Successfully loaded configuration from {config_path} in {load_time:.3f}s")
            
            if self.debug_logging:
                self.logger.debug(f"Configuration contains data source type: {self.current_config.get('data_source', {}).get('type', 'unknown')}")
                self.logger.debug(f"Time range: {self.current_config.get('time_range', {})}")
            
            return self.current_config
            
        except FileNotFoundError as e:
            load_time = time.time() - start_time
            self.operation_stats['failed_operations'] += 1
            error_msg = f"Configuration file not found: {config_path}"
            self.logger.error(f"{error_msg} (failed after {load_time:.3f}s)")
            raise FileNotFoundError(error_msg) from e
            
        except ConfigurationError as e:
            load_time = time.time() - start_time
            self.operation_stats['failed_operations'] += 1
            error_msg = f"Configuration validation failed for {config_path}: {e}"
            self.logger.error(f"{error_msg} (failed after {load_time:.3f}s)")
            raise ConfigurationError(error_msg) from e
            
        except Exception as e:
            load_time = time.time() - start_time
            self.operation_stats['failed_operations'] += 1
            error_msg = f"Unexpected error loading configuration from {config_path}: {e}"
            self.logger.error(f"{error_msg} (failed after {load_time:.3f}s)")
            raise ConfigurationError(error_msg) from e
    
    def get_data_source(self, source_type: Optional[str] = None) -> DataSourceInterface:
        """
        Get data source implementation based on configuration or specified type.
        
        Args:
            source_type: Optional data source type. If None, uses current config.
        
        Returns:
            DataSourceInterface: Instance of the appropriate data source implementation
        
        Raises:
            ValueError: If source_type is not registered or configuration is missing
            ConfigurationError: If no configuration is loaded and source_type is None
        """
        start_time = time.time()
        
        try:
            if self.debug_logging:
                self.logger.debug(f"Getting data source for type: {source_type}")
            
            if source_type is None:
                if self.current_config is None:
                    error_msg = "No configuration loaded. Call load_config() first or provide source_type."
                    self.logger.error(error_msg)
                    raise ConfigurationError(error_msg)
                source_type = self.current_config["data_source"]["type"]
                
                if self.debug_logging:
                    self.logger.debug(f"Using data source type from config: {source_type}")
            
            if source_type not in self.data_source_registry:
                available_types = list(self.data_source_registry.keys())
                error_msg = f"Unknown data source type '{source_type}'. Available types: {available_types}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Create new instance of the data source
            source_class = self.data_source_registry[source_type]
            
            if self.debug_logging:
                self.logger.debug(f"Creating instance of {source_class.__name__}")
            
            data_source = source_class()
            
            # Connect using current configuration if available
            if self.current_config is not None:
                connection_config = self.current_config["data_source"]["connection"]
                connection_start = time.time()
                
                try:
                    self.operation_stats['connection_attempts'] += 1
                    
                    if self.debug_logging:
                        self.logger.debug(f"Attempting connection to {source_type} with config: {list(connection_config.keys())}")
                    
                    if not data_source.connect(connection_config):
                        connection_time = time.time() - connection_start
                        error_msg = f"Failed to connect to {source_type} data source"
                        self.logger.error(f"{error_msg} (connection attempt took {connection_time:.3f}s)")
                        self.operation_stats['failed_operations'] += 1
                        raise ConnectionError(error_msg)
                    
                    connection_time = time.time() - connection_start
                    self.logger.info(f"Successfully connected to {source_type} data source in {connection_time:.3f}s")
                    
                except Exception as e:
                    connection_time = time.time() - connection_start
                    error_msg = f"Connection failed for {source_type} data source: {e}"
                    self.logger.error(f"{error_msg} (connection attempt took {connection_time:.3f}s)")
                    self.operation_stats['failed_operations'] += 1
                    raise ConnectionError(error_msg) from e
            
            total_time = time.time() - start_time
            
            if self.debug_logging:
                self.logger.debug(f"Data source creation completed in {total_time:.3f}s")
            
            return data_source
            
        except Exception as e:
            total_time = time.time() - start_time
            self.operation_stats['failed_operations'] += 1
            self.logger.error(f"Failed to get data source (took {total_time:.3f}s): {e}")
            raise
    
    def retrieve_metrics(
        self, 
        products: List[str], 
        time_range: Optional[TimeRange] = None,
        data_source: Optional[DataSourceInterface] = None
    ) -> pd.DataFrame:
        """
        Retrieve business metrics for specified products and time range.
        
        Args:
            products: List of product identifiers to retrieve metrics for
            time_range: Optional TimeRange. If None, uses current config time range.
            data_source: Optional data source instance. If None, creates from config.
        
        Returns:
            pd.DataFrame: Standardized business metrics
        
        Raises:
            ConfigurationError: If no configuration is loaded and time_range is None
            ValueError: If products list is empty or time_range is invalid
            DataNotFoundError: If no data exists for specified criteria
        """
        start_time = time.time()
        
        try:
            if self.debug_logging:
                self.logger.debug(f"Starting metrics retrieval for {len(products) if products else 0} products")
            
            # Input validation
            if not products:
                error_msg = "Products list cannot be empty"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            
            if self.debug_logging:
                self.logger.debug(f"Products to retrieve: {products[:5]}{'...' if len(products) > 5 else ''}")
            
            # Use provided time range or get from configuration
            if time_range is None:
                if self.current_config is None:
                    error_msg = "No configuration loaded. Provide time_range or call load_config() first."
                    self.logger.error(error_msg)
                    raise ConfigurationError(error_msg)
                
                time_config = self.current_config["time_range"]
                time_range = TimeRange.from_strings(
                    time_config["start_date"],
                    time_config["end_date"]
                )
                
                if self.debug_logging:
                    self.logger.debug(f"Using time range from config: {time_range.start_date} to {time_range.end_date}")
            
            # Use provided data source or get from configuration
            if data_source is None:
                if self.debug_logging:
                    self.logger.debug("No data source provided, getting from configuration")
                data_source = self.get_data_source()
            
            # Validate connection before retrieval
            validation_start = time.time()
            if not data_source.validate_connection():
                validation_time = time.time() - validation_start
                error_msg = "Data source connection is not valid"
                self.logger.error(f"{error_msg} (validation took {validation_time:.3f}s)")
                self.operation_stats['failed_operations'] += 1
                raise ConnectionError(error_msg)
            
            validation_time = time.time() - validation_start
            if self.debug_logging:
                self.logger.debug(f"Connection validation passed in {validation_time:.3f}s")
            
            # Retrieve metrics
            retrieval_start = time.time()
            self.operation_stats['data_retrievals'] += 1
            
            metrics = data_source.retrieve_business_metrics(
                products=products,
                start_date=time_range.start_date.strftime("%Y-%m-%d"),
                end_date=time_range.end_date.strftime("%Y-%m-%d")
            )
            
            retrieval_time = time.time() - retrieval_start
            total_time = time.time() - start_time
            
            self.operation_stats['total_retrieval_time'] += retrieval_time
            
            # Data quality validation
            quality_issues = self._validate_metrics_quality(metrics)
            if quality_issues:
                for issue in quality_issues:
                    self.logger.warning(f"Data quality issue detected: {issue}")
            
            self.logger.info(
                f"Successfully retrieved metrics for {len(products)} products "
                f"from {time_range.start_date.strftime('%Y-%m-%d')} to {time_range.end_date.strftime('%Y-%m-%d')} "
                f"in {total_time:.3f}s (retrieval: {retrieval_time:.3f}s). Retrieved {len(metrics)} records."
            )
            
            if self.debug_logging:
                self.logger.debug(f"Metrics columns: {list(metrics.columns) if not metrics.empty else 'No data'}")
                if not metrics.empty:
                    self.logger.debug(f"Date range in data: {metrics['date'].min()} to {metrics['date'].max()}")
            
            # Check for performance threshold (configurable, default 10 seconds)
            performance_threshold = 10.0
            if total_time > performance_threshold:
                self.logger.warning(
                    f"Performance threshold exceeded: operation took {total_time:.3f}s "
                    f"(threshold: {performance_threshold}s). Consider optimization."
                )
            
            return metrics
            
        except ValueError as e:
            total_time = time.time() - start_time
            self.operation_stats['failed_operations'] += 1
            self.logger.error(f"Input validation error (after {total_time:.3f}s): {e}")
            raise
            
        except ConfigurationError as e:
            total_time = time.time() - start_time
            self.operation_stats['failed_operations'] += 1
            self.logger.error(f"Configuration error (after {total_time:.3f}s): {e}")
            raise
            
        except ConnectionError as e:
            total_time = time.time() - start_time
            self.operation_stats['failed_operations'] += 1
            self.logger.error(f"Connection error (after {total_time:.3f}s): {e}")
            raise
            
        except DataNotFoundError as e:
            total_time = time.time() - start_time
            # This is not necessarily an error, just no data available
            self.logger.info(f"No data found for specified criteria (after {total_time:.3f}s): {e}")
            raise
            
        except Exception as e:
            total_time = time.time() - start_time
            self.operation_stats['failed_operations'] += 1
            error_msg = f"Unexpected error during metrics retrieval (after {total_time:.3f}s): {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def get_available_data_sources(self) -> List[str]:
        """
        Get list of available data source types.
        
        Returns:
            List[str]: List of registered data source type identifiers
        """
        return list(self.data_source_registry.keys())
    
    def get_current_config(self) -> Optional[Dict[str, Any]]:
        """
        Get the currently loaded configuration.
        
        Returns:
            Optional[Dict[str, Any]]: Current configuration or None if not loaded
        """
        return self.current_config
    
    def _validate_metrics_quality(self, metrics: pd.DataFrame) -> List[str]:
        """
        Validate data quality and return list of issues found.
        
        Args:
            metrics: DataFrame containing business metrics
        
        Returns:
            List[str]: List of data quality issues detected
        """
        issues = []
        
        if metrics.empty:
            return issues  # Empty data is not necessarily a quality issue
        
        # Required columns based on standardized schema
        required_columns = [
            'asin', 'name', 'category', 'price', 'date',
            'sales_volume', 'revenue', 'inventory_level', 'customer_engagement',
            'data_source', 'retrieval_timestamp'
        ]
        
        # Check for missing required columns
        missing_columns = [col for col in required_columns if col not in metrics.columns]
        if missing_columns:
            issues.append(f"Missing required columns: {missing_columns}")
        
        # Check for null values in critical fields
        critical_fields = ['asin', 'date', 'data_source']
        for field in critical_fields:
            if field in metrics.columns and metrics[field].isnull().any():
                null_count = metrics[field].isnull().sum()
                issues.append(f"Null values in critical field '{field}': {null_count} records")
        
        # Check for invalid data types
        if 'price' in metrics.columns:
            non_numeric_prices = metrics['price'].apply(lambda x: not isinstance(x, (int, float)) if pd.notnull(x) else False).sum()
            if non_numeric_prices > 0:
                issues.append(f"Non-numeric price values: {non_numeric_prices} records")
        
        if 'sales_volume' in metrics.columns:
            negative_sales = (metrics['sales_volume'] < 0).sum()
            if negative_sales > 0:
                issues.append(f"Negative sales volume values: {negative_sales} records")
        
        # Check for inconsistent date formats
        if 'date' in metrics.columns:
            try:
                pd.to_datetime(metrics['date'])
            except Exception:
                issues.append("Inconsistent or invalid date formats detected")
        
        return issues
    
    def get_operation_stats(self) -> Dict[str, Any]:
        """
        Get performance and operation statistics.
        
        Returns:
            Dict[str, Any]: Dictionary containing operation statistics
        """
        stats = self.operation_stats.copy()
        
        # Calculate derived metrics
        if stats['data_retrievals'] > 0:
            stats['avg_retrieval_time'] = stats['total_retrieval_time'] / stats['data_retrievals']
        else:
            stats['avg_retrieval_time'] = 0.0
        
        if stats['connection_attempts'] > 0:
            stats['connection_success_rate'] = (
                (stats['connection_attempts'] - stats['failed_operations']) / stats['connection_attempts']
            )
        else:
            stats['connection_success_rate'] = 0.0
        
        return stats
    
    def reset_stats(self) -> None:
        """Reset operation statistics."""
        self.operation_stats = {
            'config_loads': 0,
            'data_retrievals': 0,
            'connection_attempts': 0,
            'total_retrieval_time': 0.0,
            'failed_operations': 0
        }
        self.logger.info("Operation statistics reset")
    
    def enable_debug_logging(self) -> None:
        """Enable debug logging for detailed execution traces."""
        self.debug_logging = True
        self.logger.setLevel(logging.DEBUG)
        self.logger.debug("Debug logging enabled")
    
    def disable_debug_logging(self) -> None:
        """Disable debug logging."""
        self.debug_logging = False
        self.logger.setLevel(logging.INFO)
        self.logger.info("Debug logging disabled")