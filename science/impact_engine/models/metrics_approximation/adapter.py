"""Metrics Approximation Adapter - approximates impact from metric changes.

This model approximates treatment impact by correlating metric changes
(e.g., quality score improvements) with expected outcome changes via
configurable response functions.
"""

import logging
from typing import Any, Dict, List

import pandas as pd

from ..base import ModelInterface, ModelResult
from ..factory import MODEL_REGISTRY
from .response_registry import get_response_function


@MODEL_REGISTRY.register_decorator("metrics_approximation")
class MetricsApproximationAdapter(ModelInterface):
    """
    Adapter for metrics-based impact approximation that implements ModelInterface.

    This model takes enriched products with before/after metric values and baseline
    outcomes, then applies a response function to approximate the treatment impact.

    Input DataFrame must contain:
        - metric_before_column: Pre-intervention metric value
        - metric_after_column: Post-intervention metric value
        - baseline_column: Baseline sales/revenue

    Configuration:
        MEASUREMENT:
            MODEL: "metrics_approximation"
            METRIC_BEFORE_COLUMN: "quality_before"
            METRIC_AFTER_COLUMN: "quality_after"
            BASELINE_COLUMN: "baseline_sales"
            RESPONSE:
                FUNCTION: "linear"
                PARAMS:
                    coefficient: 0.5
    """

    def __init__(self):
        """Initialize the MetricsApproximationAdapter."""
        self.logger = logging.getLogger(__name__)
        self.is_connected = False
        self.config = None

    def connect(self, config: Dict[str, Any]) -> bool:
        """Initialize model with configuration parameters.

        Config is pre-validated with defaults merged via process_config().

        Args:
            config: Dictionary containing model configuration:
                - metric_before_column: Column name for pre-intervention metric
                - metric_after_column: Column name for post-intervention metric
                - baseline_column: Column name for baseline outcome
                - response: Dict with FUNCTION name and optional PARAMS

        Returns:
            bool: True if initialization successful
        """
        # Config has defaults merged from process_config()
        metric_before = config["metric_before_column"]
        metric_after = config["metric_after_column"]
        baseline = config["baseline_column"]

        # Response config has defaults from config_defaults.yaml
        response_config = config["RESPONSE"]
        if not isinstance(response_config, dict):
            raise ValueError("RESPONSE must be a dict with FUNCTION key")

        function_name = response_config.get("FUNCTION")
        if not function_name:
            raise ValueError("RESPONSE must have FUNCTION key - FUNCTION is required")

        # Validate that the response function exists
        try:
            get_response_function(function_name)
        except ValueError as e:
            raise ValueError(f"Invalid response function: {e}")

        self.config = {
            "metric_before_column": metric_before,
            "metric_after_column": metric_after,
            "baseline_column": baseline,
            "response_function": function_name,
            "response_params": response_config.get("PARAMS", {}),
        }
        self.is_connected = True
        return True

    def validate_connection(self) -> bool:
        """Validate that the model is properly initialized and ready to use."""
        return self.is_connected and self.config is not None

    def validate_params(self, params: Dict[str, Any]) -> None:
        """Validate metrics approximation parameters.

        Metrics approximation has no required fit-time parameters beyond what's
        configured in connect(). This implementation satisfies the abstract method
        requirement while allowing all params.

        Args:
            params: Parameters dict (typically empty for this model).
        """
        # No required fit-time params for metrics approximation
        pass

    def fit(self, data: pd.DataFrame, **kwargs) -> ModelResult:
        """
        Fit the metrics approximation model and return results.

        For each product, computes:
            delta_metric = metric_after - metric_before
            approximated_impact = response_function(delta_metric, baseline, row_attributes)

        Args:
            data: DataFrame with enriched products (only treated products).
                  Must contain metric_before, metric_after, and baseline columns.
                  Additional columns are passed as row_attributes to response function.
            **kwargs: Additional parameters passed to response function.

        Returns:
            ModelResult: Standardized result container (storage handled by manager).

        Raises:
            ConnectionError: If model not connected
            ValueError: If data validation fails
        """
        if not self.is_connected:
            raise ConnectionError("Model not connected. Call connect() first.")

        if not self.validate_data(data):
            raise ValueError(
                f"Data validation failed. Required columns: {self.get_required_columns()}"
            )

        # Get column names from config
        metric_before_col = self.config["metric_before_column"]
        metric_after_col = self.config["metric_after_column"]
        baseline_col = self.config["baseline_column"]

        # Get response function and params
        response_fn = get_response_function(self.config["response_function"])
        response_params = {**self.config["response_params"], **kwargs}

        # Work on a copy to avoid modifying input data
        df = data.copy()

        # Filter rows with missing values in required columns
        required_columns = [metric_before_col, metric_after_col, baseline_col]
        df = self._filter_missing_values(
            df, required_columns, kwargs["storage"], kwargs["output_path"]
        )

        # Vectorize delta computation
        df["_delta_metric"] = df[metric_after_col] - df[metric_before_col]

        # Use apply() instead of iterrows() for better performance
        # Pass row_attributes to enable attribute-based conditioning in response functions
        def compute_impact(row):
            return response_fn(
                row["_delta_metric"],
                row[baseline_col],
                row_attributes=row.to_dict(),
                **response_params,
            )

        df["_impact"] = df.apply(compute_impact, axis=1)

        # Build per-product results
        def build_product_result(row):
            return {
                "product_id": row.get("product_id", str(row.name)),
                "delta_metric": round(row["_delta_metric"], 4),
                "baseline_outcome": round(row[baseline_col], 2),
                "approximated_impact": round(row["_impact"], 2),
            }

        per_product = df.apply(build_product_result, axis=1).tolist()

        # Compute aggregates from vectorized columns
        total_impact = df["_impact"].sum()
        total_delta = df["_delta_metric"].sum()
        n_products = len(df)

        # Build aggregate estimates
        impact_estimates = {
            "total_approximated_impact": round(total_impact, 2),
            "mean_approximated_impact": round(total_impact / n_products, 2)
            if n_products > 0
            else 0.0,
            "mean_metric_change": round(total_delta / n_products, 4) if n_products > 0 else 0.0,
            "n_products": n_products,
        }

        self.logger.info(
            f"Metrics approximation complete: {n_products} products, "
            f"total impact={impact_estimates['total_approximated_impact']}"
        )

        return ModelResult(
            model_type="metrics_approximation",
            data={
                "response_function": self.config["response_function"],
                "response_params": self.config["response_params"],
                "impact_estimates": impact_estimates,
                "per_product": per_product,
            },
        )

    def validate_data(self, data: pd.DataFrame) -> bool:
        """Validate that the input data meets model requirements.

        Args:
            data: DataFrame to validate

        Returns:
            bool: True if data is valid, False otherwise
        """
        if data is None or data.empty:
            self.logger.warning("Data is empty")
            return False

        required_cols = self.get_required_columns()
        missing_cols = [col for col in required_cols if col not in data.columns]

        if missing_cols:
            self.logger.warning(f"Missing required columns: {missing_cols}")
            return False

        return True

    def get_required_columns(self) -> List[str]:
        """Get the list of required columns for this model.

        Returns:
            List[str]: Column names that must be present in input data
        """
        if not self.config:
            return ["quality_before", "quality_after", "baseline_sales"]

        return [
            self.config["metric_before_column"],
            self.config["metric_after_column"],
            self.config["baseline_column"],
        ]

    def _filter_missing_values(
        self,
        df: pd.DataFrame,
        required_columns: List[str],
        storage,
        output_path: str,
    ) -> pd.DataFrame:
        """Filter rows with missing values in required columns and log them.

        Args:
            df: DataFrame to filter
            required_columns: Columns to check for NaN/None values
            storage: Storage backend for writing filtered products CSV
            output_path: Output path for CSV file

        Returns:
            Filtered DataFrame with missing value rows removed
        """
        mask = df[required_columns].notna().all(axis=1)
        filtered_ids = df.loc[~mask, "product_id"].tolist()

        if filtered_ids:
            self.logger.warning(
                f"Filtered {len(filtered_ids)} rows with missing values in columns "
                f"{required_columns}. See filtered_products.csv for details."
            )
            filtered_df = pd.DataFrame({"product_id": filtered_ids})
            filtered_path = f"{output_path}/filtered_products.csv"
            storage.write_csv(filtered_path, filtered_df)

        return df[mask].copy()
