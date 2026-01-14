"""
Catalog Simulator Adapter - adapts online_retail_simulator package to MetricsInterface.

Integration is governed by contracts (schemas) and config bridge (config translation).
"""

import os
import tempfile
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd
import yaml
from artifact_store import JobInfo, create_job

from ..core import ConfigBridge, MetricsSchema, ProductSchema
from .base import MetricsInterface


class CatalogSimulatorAdapter(MetricsInterface):
    """Adapter for catalog simulator that implements MetricsInterface."""

    def __init__(self):
        """Initialize the CatalogSimulatorAdapter."""
        self.is_connected = False
        self.config = None
        self.parent_job: Optional[JobInfo] = None
        self.simulation_job: Optional[JobInfo] = None
        self.available_metrics = [
            "sales_volume",
            "revenue",
        ]

    def connect(self, config: Dict[str, Any]) -> bool:
        """Establish connection to the catalog simulator.

        Args:
            config: Connection configuration. When called through process_config(),
                all keys are guaranteed. When called directly (e.g., unit tests),
                defaults are applied here for backward compatibility.

        Note: Primary defaults are in config_defaults.yaml. These fallbacks
        ensure direct adapter usage (without process_config) still works.
        """
        mode = config.get("mode", "rule")
        if mode not in ["rule", "ml"]:
            raise ValueError(f"Invalid simulator mode '{mode}'. Must be 'rule' or 'ml'")

        seed = config.get("seed", 42)
        if not isinstance(seed, int) or seed < 0:
            raise ValueError("Simulator seed must be a non-negative integer")

        # Store parent job for nested job creation
        self.parent_job = config.get("parent_job")

        # Storage path for standalone jobs (when no parent_job)
        # Allows tests to pass temp directories instead of hardcoded "output"
        storage_path = config.get("storage_path", "output")

        self.config = {
            "mode": mode,
            "seed": seed,
            "storage_path": storage_path,
        }

        # Store enrichment config if provided
        enrichment = config.get("enrichment")
        if enrichment:
            self.config["enrichment"] = enrichment

        self.is_connected = True
        return True

    def retrieve_business_metrics(
        self, products: pd.DataFrame, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """Retrieve business metrics using catalog simulator's job-aware API."""
        if not self.is_connected:
            raise ConnectionError("Not connected to simulator. Call connect() first.")

        if products is None or len(products) == 0:
            raise ValueError("Products DataFrame cannot be empty")

        try:
            from online_retail_simulator.simulate import simulate_metrics

            # 1. Create nested job for simulation artifacts
            self._create_simulation_job()

            # 2. Transform input and save products to job (simulate_metrics expects them there)
            transformed_input = self.transform_outbound(products, start_date, end_date)
            self.simulation_job.save_df("products", transformed_input["product_characteristics"])

            # 3. Build full simulator config
            simulator_config = {"RULE": transformed_input["rule_config"]}

            # 4. Write config to temp file for simulate_metrics
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                yaml.dump(simulator_config, f)
                config_path = f.name

            try:
                # 5. Call catalog_simulator's simulate_metrics (handles backend + storage)
                simulate_metrics(self.simulation_job, config_path)
            finally:
                # Clean up temp file
                os.unlink(config_path)

            # 6. Load metrics from job (simulate_metrics saves as "metrics")
            sales_df = self.simulation_job.load_df("metrics")

            # 7. Apply enrichment if configured
            if self.config.get("enrichment"):
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
            self.simulation_job = create_job(
                self.parent_job.full_path, prefix="job-catalog-simulator-simulation"
            )
        else:
            # Create standalone job using configured storage path
            self.simulation_job = create_job(
                self.config["storage_path"], prefix="job-catalog-simulator-simulation"
            )

    def _apply_enrichment(self, metrics_df: pd.DataFrame) -> pd.DataFrame:
        """Apply enrichment and add quality_score to metrics based on enrichment_start date.

        This method:
        1. Calls simulate_product_details() to generate product_details (needed by enrich)
        2. Calls enrich() which creates product_details_original and product_details_enriched
        3. Joins quality_score to metrics based on date vs enrichment_start

        Returns metrics DataFrame with quality_score column added.
        """
        from online_retail_simulator.enrich import enrich
        from online_retail_simulator.simulate import simulate_product_details

        # Generate product_details (required by enrich)
        product_details_config = {
            "PRODUCT_DETAILS": {
                "FUNCTION": "simulate_product_details_mock",
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(product_details_config, f)
            pd_config_path = f.name

        try:
            self.simulation_job = simulate_product_details(self.simulation_job, pd_config_path)
        finally:
            os.unlink(pd_config_path)

        # Use config bridge to build IMPACT config
        impact_config = ConfigBridge.build_enrichment_config(self.config["enrichment"])

        # Write config to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(impact_config, f)
            config_path = f.name

        try:
            # Apply enrichment (creates product_details_original, product_details_enriched)
            self.simulation_job = enrich(config_path, self.simulation_job)
        finally:
            os.unlink(config_path)

        # Load original and enriched product details
        products_original = self.simulation_job.load_df("product_details_original")
        products_enriched = self.simulation_job.load_df("product_details_enriched")

        # Get enrichment_start from config
        enrichment_params = self.config["enrichment"].get("params", {})
        enrichment_start = enrichment_params.get("enrichment_start", "2024-11-15")
        enrichment_date = pd.to_datetime(enrichment_start)

        # Create quality lookup by product
        orig_quality = products_original.set_index("product_identifier")["quality_score"].to_dict()
        enr_quality = products_enriched.set_index("product_identifier")["quality_score"].to_dict()

        # Add quality_score to metrics based on date
        result = metrics_df.copy()
        result["date"] = pd.to_datetime(result["date"])

        # Detect product ID column
        id_col = "product_identifier" if "product_identifier" in result.columns else "product_id"

        result["quality_score"] = result.apply(
            lambda row: (
                orig_quality.get(row[id_col], 0.5)
                if row["date"] < enrichment_date
                else enr_quality.get(row[id_col], 0.5)
            ),
            axis=1,
        )

        return result

    def validate_connection(self) -> bool:
        """Validate that the catalog simulator connection is active and functional."""
        if not self.is_connected:
            return False

        try:
            from online_retail_simulator.core import RuleBackend  # noqa: F401

            return True
        except ImportError:
            return False

    def transform_outbound(
        self, products: pd.DataFrame, start_date: str, end_date: str
    ) -> Dict[str, Any]:
        """Transform impact engine format to catalog simulator format using contracts."""
        product_characteristics = products.copy()

        # Ensure product_id exists before transformation
        if "product_id" not in product_characteristics.columns:
            # Try to find a suitable ID column
            id_columns = [
                col
                for col in product_characteristics.columns
                if "id" in col.lower() or col.lower() in ["product", "sku", "code"]
            ]
            if id_columns:
                product_characteristics["product_id"] = product_characteristics[id_columns[0]]
            else:
                product_characteristics["product_id"] = product_characteristics.index.astype(str)

        # Use contract to transform product_id → asin
        product_characteristics = ProductSchema.to_external(
            product_characteristics, "catalog_simulator"
        )

        # Use config bridge to build simulator config
        ie_config = {
            "DATA": {
                "START_DATE": start_date,
                "END_DATE": end_date,
                "SEED": self.config["seed"],
            }
        }
        cs_config = ConfigBridge.to_catalog_simulator(
            ie_config, num_products=len(product_characteristics)
        )

        return {
            "product_characteristics": product_characteristics,
            "rule_config": cs_config["RULE"],
        }

    def transform_inbound(self, external_data: Any) -> pd.DataFrame:
        """Transform catalog simulator response to impact engine format using contracts."""
        if not isinstance(external_data, pd.DataFrame):
            raise ValueError("Expected pandas DataFrame from catalog simulator")

        if external_data.empty:
            return pd.DataFrame(columns=MetricsSchema.all_columns())

        # Handle case where both asin and product_identifier exist - prefer product_identifier
        df = external_data.copy()
        if "product_identifier" in df.columns and "asin" in df.columns:
            df = df.drop(columns=["asin"])

        # Use contract to transform product_identifier/asin → product_id, ordered_units → sales_volume
        standardized = MetricsSchema.from_external(df, "catalog_simulator")

        # Handle legacy 'quantity' column (not in contract, manual fallback)
        if "quantity" in standardized.columns and "sales_volume" not in standardized.columns:
            standardized["sales_volume"] = standardized["quantity"]
            standardized.drop("quantity", axis=1, inplace=True)

        # Ensure date column is datetime
        if "date" in standardized.columns:
            standardized["date"] = pd.to_datetime(standardized["date"])

        # Add metadata fields
        standardized["metrics_source"] = "catalog_simulator"
        standardized["retrieval_timestamp"] = datetime.now()

        # Ensure proper data types
        if "price" in standardized.columns:
            standardized["price"] = pd.to_numeric(standardized["price"], errors="coerce")
        if "revenue" in standardized.columns:
            standardized["revenue"] = pd.to_numeric(standardized["revenue"], errors="coerce")
        if "sales_volume" in standardized.columns:
            standardized["sales_volume"] = (
                pd.to_numeric(standardized["sales_volume"], errors="coerce").fillna(0).astype(int)
            )

        # Reorder columns to match schema (required + optional)
        column_order = MetricsSchema.all_columns()
        available_columns = [col for col in column_order if col in standardized.columns]
        return standardized[available_columns]
