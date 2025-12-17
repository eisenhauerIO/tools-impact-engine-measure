"""
Simulator data source implementation for the online_retail_simulator package.
"""

import pandas as pd
import logging
from typing import Dict, List, Any
from datetime import datetime
import tempfile
import json
import os

from .base import DataSourceInterface, DataNotFoundError, TimeRange


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
        existing_products = all_products[all_products['asin'].isin(requested_products)]
        
        # Create missing products with default values
        missing_asins = set(requested_products) - set(existing_products['asin'])
        
        if missing_asins:
            self.logger.warning(f"Creating default entries for missing products: {list(missing_asins)}")
            
            missing_products = []
            for asin in missing_asins:
                missing_products.append({
                    'asin': asin,
                    'name': f'Product {asin}',
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
        
        The simulator returns: asin, name, category, price, date, quantity, revenue
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
                'asin', 'name', 'category', 'price', 'date',
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
                'asin', 'name', 'category', 'price', 'date',
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
            'asin', 'name', 'category', 'price', 'date',
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