"""
Catalog Simulator Adapter - adapts online_retail_simulator package to MetricsInterface.
"""

import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime

from artifact_store import JobInfo, create_job
from .base import MetricsInterface


class CatalogSimulatorAdapter(MetricsInterface):
    """Adapter for catalog simulator that implements MetricsInterface."""

    def __init__(self):
        """Initialize the CatalogSimulatorAdapter."""
        self.is_connected = False
        self.config = None
        self.parent_job: Optional[JobInfo] = None
        self.simulation_job: Optional[JobInfo] = None
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

        # Store parent job for nested job creation
        self.parent_job = config.get('parent_job')

        self.config = {
            'mode': mode,
            'seed': seed,
        }

        # Store enrichment config if provided
        enrichment = config.get('enrichment')
        if enrichment:
            self.config['enrichment'] = enrichment

        self.is_connected = True
        return True
    
    def retrieve_business_metrics(self, products: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
        """Retrieve business metrics using catalog simulator's job-aware API."""
        if not self.is_connected:
            raise ConnectionError("Not connected to simulator. Call connect() first.")

        if products is None or len(products) == 0:
            raise ValueError("Products DataFrame cannot be empty")

        try:
            from online_retail_simulator.simulate import simulate_metrics
            import tempfile
            import yaml
            import os

            # 1. Create nested job for simulation artifacts
            self._create_simulation_job()

            # 2. Transform input and save products to job (simulate_metrics expects them there)
            transformed_input = self.transform_outbound(products, start_date, end_date)
            self.simulation_job.save_df("products", transformed_input["product_characteristics"])

            # 3. Build full simulator config
            simulator_config = {"RULE": transformed_input["rule_config"]}

            # 4. Write config to temp file for simulate_metrics
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml.dump(simulator_config, f)
                config_path = f.name

            try:
                # 5. Call catalog_simulator's simulate_metrics (handles backend + storage)
                simulate_metrics(self.simulation_job, config_path)
            finally:
                # Clean up temp file
                os.unlink(config_path)

            # 6. Load sales from job
            sales_df = self.simulation_job.load_df("sales")

            # 7. Apply enrichment if configured
            if self.config.get('enrichment'):
                sales_df = self._apply_enrichment(sales_df)

            # 8. Transform to impact engine format
            return self.transform_inbound(sales_df)

        except ImportError as e:
            raise ConnectionError(f"online_retail_simulator package not available: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve metrics: {e}")

    def _create_simulation_job(self) -> None:
        """Create a job for simulation artifacts. Uses nested job if parent provided."""
        if self.parent_job is not None:
            # Create nested job inside parent job directory
            self.simulation_job = create_job(self.parent_job.full_path, prefix="job-catalog-simulator-simulation")
        else:
            # Create standalone job in default output directory
            self.simulation_job = create_job("output", prefix="job-catalog-simulator-simulation")

    def _apply_enrichment(self, sales_df: pd.DataFrame) -> pd.DataFrame:
        """Apply enrichment using catalog simulator's config-based interface."""
        from online_retail_simulator.enrich.enrichment import enrich

        # Create job for enrichment artifacts
        if self.parent_job is not None:
            enrichment_job = create_job(self.parent_job.full_path, prefix="job-catalog-simulator-enrichment")
        else:
            enrichment_job = create_job("output", prefix="job-catalog-simulator-enrichment")

        # Build catalog simulator IMPACT config format
        impact_config = {
            "IMPACT": {
                "FUNCTION": self.config['enrichment']['function'],
                "PARAMS": self.config['enrichment']['params']
            }
        }

        # Write config to enrichment job
        enrichment_store = enrichment_job.get_store()
        config_path = enrichment_store.full_path("config.yaml")
        enrichment_store.write_yaml("config.yaml", impact_config)

        # Apply enrichment
        enriched_df = enrich(config_path, sales_df)

        # Save enriched output
        enrichment_job.save_df("enriched", enriched_df)

        return enriched_df
    

    
    def validate_connection(self) -> bool:
        """Validate that the catalog simulator connection is active and functional."""
        if not self.is_connected:
            return False

        try:
            from online_retail_simulator.core import RuleBackend
            return True
        except ImportError:
            return False
    
    def transform_outbound(self, products: pd.DataFrame, start_date: str, end_date: str) -> Dict[str, Any]:
        """Transform impact engine format to catalog simulator format."""
        # Prepare products DataFrame for simulator
        product_characteristics = products.copy()

        # Handle product_id → asin mapping (RuleBackend expects 'asin')
        if 'product_id' in product_characteristics.columns:
            product_characteristics['asin'] = product_characteristics['product_id']
        elif 'asin' not in product_characteristics.columns:
            # Try to find a suitable ID column
            id_columns = [col for col in product_characteristics.columns
                        if 'id' in col.lower() or col.lower() in ['product', 'sku', 'code']]
            if id_columns:
                product_characteristics['asin'] = product_characteristics[id_columns[0]]
            else:
                # If no ID column found, create one from the index
                product_characteristics['asin'] = product_characteristics.index.astype(str)

        # Add default values for missing required columns
        if 'name' not in product_characteristics.columns:
            product_characteristics['name'] = product_characteristics['asin'].apply(lambda x: f'Product {x}')
        if 'category' not in product_characteristics.columns:
            product_characteristics['category'] = 'Electronics'  # Default category
        if 'price' not in product_characteristics.columns:
            product_characteristics['price'] = 100.0  # Default price

        # Build RuleBackend config structure
        rule_config = {
            "CHARACTERISTICS": {
                "FUNCTION": "simulate_characteristics_rule_based",
                "PARAMS": {"num_products": len(product_characteristics)}
            },
            "METRICS": {
                "FUNCTION": "simulate_metrics_rule_based",
                "PARAMS": {
                    "date_start": start_date,
                    "date_end": end_date,
                    "sale_prob": 0.7,
                    "seed": self.config['seed'],
                    "granularity": "daily",
                    "impression_to_visit_rate": 0.15,
                    "visit_to_cart_rate": 0.25,
                    "cart_to_order_rate": 0.80
                }
            }
        }

        return {
            "product_characteristics": product_characteristics,
            "rule_config": rule_config
        }
    
    def transform_inbound(self, external_data: Any) -> pd.DataFrame:
        """Transform catalog simulator response to impact engine format."""
        if not isinstance(external_data, pd.DataFrame):
            raise ValueError("Expected pandas DataFrame from catalog simulator")

        raw_metrics = external_data

        if raw_metrics.empty:
            return pd.DataFrame(columns=[
                'product_id', 'name', 'category', 'price', 'date',
                'sales_volume', 'revenue', 'inventory_level', 'customer_engagement',
                'metrics_source', 'retrieval_timestamp'
            ])

        standardized = raw_metrics.copy()

        # Map asin → product_id (RuleBackend uses 'asin')
        if 'asin' in standardized.columns:
            standardized['product_id'] = standardized['asin']
            standardized.drop('asin', axis=1, inplace=True)

        # Ensure date column is datetime
        if 'date' in standardized.columns:
            standardized['date'] = pd.to_datetime(standardized['date'])

        # Map 'ordered_units' to 'sales_volume' (RuleBackend output)
        if 'ordered_units' in standardized.columns:
            standardized['sales_volume'] = standardized['ordered_units']
            standardized.drop('ordered_units', axis=1, inplace=True)
        # Also handle legacy 'quantity' column
        elif 'quantity' in standardized.columns:
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
    
