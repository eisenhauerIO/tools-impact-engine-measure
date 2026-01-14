"""Metrics Approximation Adapter - approximates impact from metric changes.

This model approximates treatment impact by correlating metric changes
(e.g., quality score improvements) with expected outcome changes via
configurable response functions.
"""

import logging
from typing import Any, Dict, List

import pandas as pd

from ..base import Model
from .response_registry import get_response_function


class MetricsApproximationAdapter(Model):
    """
    Adapter for metrics-based impact approximation that implements Model interface.

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

        Args:
            config: Dictionary containing model configuration:
                - metric_before_column: Column name for pre-intervention metric
                - metric_after_column: Column name for post-intervention metric
                - baseline_column: Column name for baseline outcome
                - response: Dict with FUNCTION name and optional PARAMS

        Returns:
            bool: True if initialization successful
        """
        # Validate required columns
        metric_before = config.get("metric_before_column", "quality_before")
        metric_after = config.get("metric_after_column", "quality_after")
        baseline = config.get("baseline_column", "baseline_sales")

        # Validate response function configuration
        response_config = config.get("response", {"FUNCTION": "linear"})
        if not isinstance(response_config, dict):
            raise ValueError("response must be a dict with FUNCTION key")

        function_name = response_config.get("FUNCTION")
        if not function_name:
            raise ValueError("response.FUNCTION is required")

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

    def fit(self, data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Fit the metrics approximation model and return results.

        For each product, computes:
            delta_metric = metric_after - metric_before
            approximated_impact = response_function(delta_metric, baseline)

        Args:
            data: DataFrame with enriched products (only treated products).
                  Must contain metric_before, metric_after, and baseline columns.
            **kwargs: Additional parameters passed to response function.

        Returns:
            Dict containing:
                - model_type: "metrics_approximation"
                - response_function: Name of response function used
                - impact_estimates: Aggregate statistics
                - per_product: List of per-product results

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

        # Compute per-product impacts
        per_product = []
        total_impact = 0.0
        total_delta = 0.0

        for idx, row in data.iterrows():
            delta_metric = row[metric_after_col] - row[metric_before_col]
            baseline = row[baseline_col]

            # Apply response function
            impact = response_fn(delta_metric, baseline, **response_params)

            # Build per-product result
            product_result = {
                "product_id": row.get("product_id", str(idx)),
                "delta_metric": round(delta_metric, 4),
                "baseline_outcome": round(baseline, 2),
                "approximated_impact": round(impact, 2),
            }
            per_product.append(product_result)

            total_impact += impact
            total_delta += delta_metric

        n_products = len(data)

        # Build aggregate estimates
        impact_estimates = {
            "total_approximated_impact": round(total_impact, 2),
            "mean_approximated_impact": round(total_impact / n_products, 2) if n_products > 0 else 0.0,
            "mean_metric_change": round(total_delta / n_products, 4) if n_products > 0 else 0.0,
            "n_products": n_products,
        }

        results = {
            "model_type": "metrics_approximation",
            "response_function": self.config["response_function"],
            "response_params": self.config["response_params"],
            "impact_estimates": impact_estimates,
            "per_product": per_product,
        }

        self.logger.info(
            f"Metrics approximation complete: {n_products} products, "
            f"total impact={impact_estimates['total_approximated_impact']}"
        )

        return results

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
