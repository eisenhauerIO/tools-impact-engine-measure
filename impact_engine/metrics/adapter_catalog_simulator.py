"""
Catalog Simulator Adapter - adapts online_retail_simulator package to MetricsInterface.
"""

import pandas as pd
from typing import Dict, List, Any
from datetime import datetime

from .base import MetricsInterface, MetricsNotFoundError


class CatalogSimulatorAdapter(MetricsInterface):
    """Adapter for catalog simulator that implements MetricsInterface."""
    
    def __init__(self):
        """Initialize the CatalogSimulatorAdapter."""
        self.is_connected = False
        self.config = None
        self.available_metrics = ['sales_volume', 'revenue', 'inventory_level', 'customer_engagement']
    
    def connect(self, config: Dict[str, Any]) -> bool:
        """Establish connection to the catalog simulator."""
        # Validate mode
        mode = config.get('mode', 'rule')
        if mode not in ['rule', 'ml']:
            raise ValueError(f"Invalid simulator mode '{mode}'. Must be 'rule' or 'ml'")
        
        # Validate seed
        seed = config.get('seed', 42)
        if not isinstance(seed, int) or seed < 0:
            raise ValueError("Simulator seed must be a non-negative integer")
        
        self.config = {'mode': mode, 'seed': seed}
        self.is_connected = True
        return True
    
    def retrieve_business_metrics(self, products: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
        """Retrieve business metrics for specified products using catalog simulator."""
        if not self.is_connected:
            raise ConnectionError("Not connected to simulator. Call connect() first.")
        
        if products is None or len(products) == 0:
            raise ValueError("Products DataFrame cannot be empty")
        
        try:
            from online_retail_simulator import simulate_metrics
            import tempfile
            import json
            import os
            
            # Use the provided DataFrame directly
            product_characteristics = products.copy()
            
            # Ensure required columns exist
            if 'product_id' not in product_characteristics.columns:
                # Try to find a suitable ID column
                id_columns = [col for col in product_characteristics.columns 
                            if 'id' in col.lower() or col.lower() in ['product', 'sku', 'code']]
                if id_columns:
                    product_characteristics['product_id'] = product_characteristics[id_columns[0]]
                else:
                    # If no ID column found, create one from the index
                    product_characteristics['product_id'] = product_characteristics.index.astype(str)
            
            # Add default values for missing required columns
            if 'name' not in product_characteristics.columns:
                product_characteristics['name'] = product_characteristics['product_id'].apply(lambda x: f'Product {x}')
            if 'category' not in product_characteristics.columns:
                product_characteristics['category'] = 'Electronics'  # Default category
            if 'price' not in product_characteristics.columns:
                product_characteristics['price'] = 100.0  # Default price
            
            # Create config dict for simulator
            simulator_config = {
                "SIMULATOR": {"mode": self.config['mode']},
                "SEED": self.config['seed'],
                "RULE": {
                    "DATE_START": start_date,
                    "DATE_END": end_date,
                    "SALE_PROB": 0.7
                }
            }
            
            # Create temporary config file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(simulator_config, f)
                temp_config_path = f.name
            
            try:
                # Generate metrics using the simulator
                raw_metrics = simulate_metrics(
                    product_characteristics=product_characteristics,
                    config_path=temp_config_path
                )
                
                # Transform to standardized schema
                return self._transform_to_standard_schema(raw_metrics)
                
            finally:
                # Clean up temporary config file
                try:
                    os.unlink(temp_config_path)
                except OSError:
                    pass
            
        except ImportError as e:
            raise ConnectionError(f"online_retail_simulator package not available: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve metrics: {e}")
    
    def _transform_to_standard_schema(self, raw_metrics: pd.DataFrame) -> pd.DataFrame:
        """Transform simulator output to standardized business metrics schema."""
        if raw_metrics.empty:
            return pd.DataFrame(columns=[
                'product_id', 'name', 'category', 'price', 'date',
                'sales_volume', 'revenue', 'inventory_level', 'customer_engagement',
                'metrics_source', 'retrieval_timestamp'
            ])
        
        standardized = raw_metrics.copy()
        
        # Ensure date column is datetime
        if 'date' in standardized.columns:
            standardized['date'] = pd.to_datetime(standardized['date'])
        
        # Map 'quantity' to 'sales_volume' if needed
        if 'quantity' in standardized.columns:
            standardized['sales_volume'] = standardized['quantity']
            standardized.drop('quantity', axis=1, inplace=True)
        
        # Add missing standardized fields
        if 'inventory_level' not in standardized.columns:
            max_inventory = 1000
            standardized['inventory_level'] = (max_inventory - (standardized.get('sales_volume', 0) * 10)).clip(lower=0).astype(int)
        
        if 'customer_engagement' not in standardized.columns:
            # Customer engagement based on sales activity
            sales_col = standardized.get('sales_volume', pd.Series([0] * len(standardized)))
            max_sales = sales_col.max() if len(sales_col) > 0 else 1
            if max_sales > 0:
                standardized['customer_engagement'] = (sales_col / max_sales).clip(upper=1.0)
            else:
                standardized['customer_engagement'] = 0.0
            standardized['customer_engagement'] = standardized['customer_engagement'].fillna(0.0)
        
        # Add metadata fields
        standardized['metrics_source'] = 'catalog_simulator'
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
            'metrics_source', 'retrieval_timestamp'
        ]
        available_columns = [col for col in column_order if col in standardized.columns]
        return standardized[available_columns]
    
    def validate_connection(self) -> bool:
        """Validate that the catalog simulator connection is active and functional."""
        if not self.is_connected:
            return False
        
        try:
            from online_retail_simulator import simulate_metrics
            return True
        except ImportError:
            return False
    
