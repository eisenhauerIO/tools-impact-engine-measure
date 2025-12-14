"""
Data Abstraction Layer - Data Source Interface and Implementations

This module provides the abstract interface and concrete implementations for
various data sources used in business metrics retrieval for impact analysis.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import pandas as pd
from datetime import datetime
import logging
import time
from dataclasses import dataclass
from .config import ConfigurationParser, ConfigurationError


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
                - product_id (str): Unique product identifier
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


class SimulatorDataSource(DataSourceInterface):
    """
    Concrete implementation of DataSourceInterface for the online_retail_simulator package.
    
    This data source uses the online_retail_simulator package to generate business
    metrics data for testing and development purposes. It implements the standardized
    interface while handling simulator-specific configuration and data transformation.
    """
    
    def __init__(self):
        """Initialize the SimulatorDataSource."""
        self.logger = logging.getLogger(__name__)
        self.is_connected = False
        self.config = None
        self.available_metrics = [
            'sales_volume', 'revenue', 'inventory_level', 'customer_engagement'
        ]
    
    def connect(self, config: Dict[str, Any]) -> bool:
        """
        Establish connection to the simulator data source.
        
        For the simulator, this validates the configuration and sets up
        the connection parameters. No actual network connection is required.
        
        Args:
            config: Dictionary containing simulator connection parameters.
                   Expected keys: 'mode' (optional, default 'rule'), 'seed' (optional)
        
        Returns:
            bool: True if configuration is valid, False otherwise.
        
        Raises:
            ValueError: If required configuration parameters are missing or invalid.
        """
        try:
            self.logger.debug("Connecting to simulator data source")
            
            # Validate configuration structure
            if not isinstance(config, dict):
                raise ValueError("Simulator configuration must be a dictionary")
            
            # Set default values for optional parameters
            simulator_config = {
                'mode': config.get('mode', 'rule'),
                'seed': config.get('seed', 42)
            }
            
            # Validate mode
            if simulator_config['mode'] not in ['rule', 'ml']:
                raise ValueError(f"Invalid simulator mode '{simulator_config['mode']}'. Must be 'rule' or 'ml'")
            
            # Validate seed
            if not isinstance(simulator_config['seed'], int) or simulator_config['seed'] < 0:
                raise ValueError("Simulator seed must be a non-negative integer")
            
            self.config = simulator_config
            self.is_connected = True
            
            self.logger.info(f"Successfully connected to simulator with mode='{simulator_config['mode']}', seed={simulator_config['seed']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to simulator: {e}")
            self.is_connected = False
            raise ValueError(f"Simulator connection failed: {e}")
    
    def retrieve_business_metrics(
        self, 
        products: List[str], 
        start_date: str, 
        end_date: str
    ) -> pd.DataFrame:
        """
        Retrieve business metrics for specified products and time range from simulator.
        
        This method uses the online_retail_simulator package to generate metrics data.
        It first gets product characteristics, then generates time-series metrics,
        and finally transforms the data to match the standardized schema.
        
        Args:
            products: List of product identifiers to retrieve metrics for
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)
        
        Returns:
            pd.DataFrame: Standardized business metrics with required schema
        
        Raises:
            ConnectionError: If not connected to simulator
            ValueError: If date range is invalid or products list is empty
            DataNotFoundError: If no data exists for specified products/time range
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to simulator. Call connect() first.")
        
        if not products:
            raise ValueError("Products list cannot be empty")
        
        # Validate date format and range
        time_range = TimeRange.from_strings(start_date, end_date)
        
        try:
            self.logger.debug(f"Retrieving metrics for {len(products)} products from {start_date} to {end_date}")
            
            # Import simulator functions
            from online_retail_simulator import simulate_characteristics, simulate_metrics
            
            # Create temporary config file for simulator
            import tempfile
            import json
            
            simulator_config = {
                "SIMULATOR": {"mode": self.config['mode']},
                "SEED": self.config['seed'],
                "RULE": {
                    "DATE_START": start_date,
                    "DATE_END": end_date,
                    "NUM_PRODUCTS": 1000,  # Generate more products than needed
                    "SALE_PROB": 0.7
                }
            }
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(simulator_config, f)
                temp_config_path = f.name
            
            try:
                # Get all product characteristics from simulator
                all_products = simulate_characteristics(temp_config_path)
                
                # Filter to requested products or create them if they don't exist
                requested_products = self._get_or_create_products(all_products, products)
                
                if requested_products.empty:
                    raise DataNotFoundError(f"No products found matching: {products}")
                
                # Generate metrics for the requested products
                raw_metrics = simulate_metrics(requested_products, temp_config_path)
                
                # Transform to standardized schema with time range filtering
                standardized_metrics = self._transform_to_standard_schema(
                    raw_metrics, start_date, end_date
                )
                
                self.logger.info(f"Successfully retrieved {len(standardized_metrics)} metric records for {len(requested_products)} products")
                
                return standardized_metrics
                
            finally:
                # Clean up temporary config file
                import os
                try:
                    os.unlink(temp_config_path)
                except OSError:
                    pass
            
        except ImportError as e:
            raise ConnectionError(f"online_retail_simulator package not available: {e}")
        except Exception as e:
            self.logger.error(f"Error retrieving metrics from simulator: {e}")
            raise RuntimeError(f"Failed to retrieve metrics: {e}")
    
    def _get_or_create_products(self, all_products: pd.DataFrame, requested_products: List[str]) -> pd.DataFrame:
        """
        Get requested products from the generated products or create minimal entries.
        
        Args:
            all_products: DataFrame of all generated products
            requested_products: List of product IDs to retrieve
        
        Returns:
            pd.DataFrame: Products matching the requested IDs
        """
        # Filter existing products
        existing_products = all_products[all_products['product_id'].isin(requested_products)]
        
        # Create missing products with default values
        missing_product_ids = set(requested_products) - set(existing_products['product_id'])
        
        if missing_product_ids:
            self.logger.warning(f"Creating default entries for missing products: {list(missing_product_ids)}")
            
            missing_products = []
            for product_id in missing_product_ids:
                missing_products.append({
                    'product_id': product_id,
                    'name': f'Product {product_id}',
                    'category': 'Unknown',
                    'price': 100.0  # Default price
                })
            
            missing_df = pd.DataFrame(missing_products)
            result = pd.concat([existing_products, missing_df], ignore_index=True)
        else:
            result = existing_products
        
        return result
    
    def _transform_to_standard_schema(self, raw_metrics: pd.DataFrame, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Transform simulator output to standardized business metrics schema.
        
        The simulator returns: product_id, name, category, price, date, quantity, revenue
        We need to transform this to the standard schema with additional fields and
        apply time range filtering based on configuration.
        
        Args:
            raw_metrics: Raw metrics from simulator
            start_date: Optional start date for filtering (YYYY-MM-DD)
            end_date: Optional end date for filtering (YYYY-MM-DD)
        
        Returns:
            pd.DataFrame: Metrics in standardized schema
        """
        if raw_metrics.empty:
            # Return empty DataFrame with correct schema
            return pd.DataFrame(columns=[
                'product_id', 'name', 'category', 'price', 'date',
                'sales_volume', 'revenue', 'inventory_level', 'customer_engagement',
                'data_source', 'retrieval_timestamp'
            ])
        
        # Start with a copy of the raw metrics
        standardized = raw_metrics.copy()
        
        # Ensure date column is datetime for filtering
        if 'date' in standardized.columns:
            standardized['date'] = pd.to_datetime(standardized['date'])
        
        # Apply time range filtering if specified
        if start_date and end_date:
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            
            # Filter data to the specified time range
            date_mask = (standardized['date'] >= start_dt) & (standardized['date'] <= end_dt)
            standardized = standardized[date_mask]
            
            self.logger.debug(f"Filtered metrics to date range {start_date} to {end_date}: {len(standardized)} records")
        
        # If no data remains after filtering, return empty DataFrame with correct schema
        if standardized.empty:
            return pd.DataFrame(columns=[
                'product_id', 'name', 'category', 'price', 'date',
                'sales_volume', 'revenue', 'inventory_level', 'customer_engagement',
                'data_source', 'retrieval_timestamp'
            ])
        
        # Map 'quantity' to 'sales_volume' (core transformation requirement)
        standardized['sales_volume'] = standardized['quantity']
        standardized.drop('quantity', axis=1, inplace=True)
        
        # Add missing standardized fields with simulated values
        # Inventory level: simulate based on sales volume (higher sales = lower inventory)
        max_inventory = 1000
        standardized['inventory_level'] = (
            max_inventory - (standardized['sales_volume'] * 10)
        ).clip(lower=0).astype(int)
        
        # Customer engagement: simulate based on sales activity (0-1 scale)
        # Higher sales volume indicates higher engagement
        max_sales = standardized['sales_volume'].max()
        if max_sales > 0:
            standardized['customer_engagement'] = (
                standardized['sales_volume'] / max_sales
            ).clip(upper=1.0)
        else:
            standardized['customer_engagement'] = 0.0
        
        # Handle any remaining null values in customer_engagement
        standardized['customer_engagement'] = standardized['customer_engagement'].fillna(0.0)
        
        # Add metadata fields (requirement: data_source and retrieval_timestamp)
        standardized['data_source'] = 'simulator'
        standardized['retrieval_timestamp'] = datetime.now()
        
        # Ensure proper data types
        if 'price' in standardized.columns:
            standardized['price'] = pd.to_numeric(standardized['price'], errors='coerce')
        if 'revenue' in standardized.columns:
            standardized['revenue'] = pd.to_numeric(standardized['revenue'], errors='coerce')
        if 'sales_volume' in standardized.columns:
            standardized['sales_volume'] = pd.to_numeric(standardized['sales_volume'], errors='coerce').fillna(0).astype(int)
        
        # Reorder columns to match standard schema
        column_order = [
            'product_id', 'name', 'category', 'price', 'date',
            'sales_volume', 'revenue', 'inventory_level', 'customer_engagement',
            'data_source', 'retrieval_timestamp'
        ]
        
        # Only include columns that exist
        available_columns = [col for col in column_order if col in standardized.columns]
        standardized = standardized[available_columns]
        
        # Log transformation summary
        self.logger.debug(f"Transformed {len(standardized)} records to standard schema")
        self.logger.debug(f"Schema columns: {list(standardized.columns)}")
        
        return standardized
    
    def validate_connection(self) -> bool:
        """
        Validate that the simulator connection is active and functional.
        
        For the simulator, this checks if the connection was established
        and the configuration is valid.
        
        Returns:
            bool: True if connection is valid, False otherwise.
        """
        if not self.is_connected:
            return False
        
        try:
            # Try to import the simulator to ensure it's available
            from online_retail_simulator import simulate_characteristics
            return True
        except ImportError:
            self.logger.error("online_retail_simulator package not available")
            return False
        except Exception as e:
            self.logger.error(f"Simulator validation failed: {e}")
            return False
    
    def get_available_metrics(self) -> List[str]:
        """
        Return list of available metric types supported by the simulator.
        
        Returns:
            List[str]: List of available metric names
        """
        return self.available_metrics.copy()


class DataSourceManager:
    """
    Central coordinator for data source management and configuration.
    
    This class provides the main interface for the data abstraction layer,
    handling configuration loading, data source selection, and coordinating
    data retrieval operations across different data source implementations.
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
        
        Args:
            source_type: String identifier for the data source type
            source_class: Class implementing DataSourceInterface
        
        Raises:
            ValueError: If source_class doesn't implement DataSourceInterface
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
            'product_id', 'name', 'category', 'price', 'date',
            'sales_volume', 'revenue', 'inventory_level', 'customer_engagement',
            'data_source', 'retrieval_timestamp'
        ]
        
        # Check for missing required columns
        missing_columns = [col for col in required_columns if col not in metrics.columns]
        if missing_columns:
            issues.append(f"Missing required columns: {missing_columns}")
        
        # Check for null values in critical fields
        critical_fields = ['product_id', 'date', 'data_source']
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