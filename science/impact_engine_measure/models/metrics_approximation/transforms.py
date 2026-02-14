"""
Transforms specific to the Metrics Approximation model.

These transforms prepare data for metrics approximation by creating
cross-sectional summaries from time-series data.
"""

from typing import Any, Dict

import pandas as pd

from ...core import register_transform


@register_transform("aggregate_for_approximation")
def aggregate_for_approximation(data: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """Aggregate data for metrics approximation models.

    This transform creates cross-sectional data for approximation models.
    It computes baseline metrics per product, suitable for before/after analysis.

    Args:
        data: Input DataFrame with 'product_id' column and metrics.
        params: Configuration parameters:
            - baseline_metric (str): The metric to aggregate as baseline (default: "revenue").

    Returns:
        pd.DataFrame: Cross-sectional data with columns:
            - product_id: Product identifier
            - baseline_sales: Aggregated baseline metric per product

    Raises:
        ValueError: If required columns are missing.
    """
    baseline_metric = params.get("baseline_metric", "revenue")

    # Require 'product_id' column
    if "product_id" not in data.columns:
        raise ValueError("Data must contain 'product_id' column for aggregate_for_approximation")
    id_column = "product_id"

    if baseline_metric not in data.columns:
        raise ValueError(f"Data must contain baseline metric column '{baseline_metric}'")

    # Aggregate baseline metric per product
    aggregated = data.groupby(id_column).agg({baseline_metric: "sum"}).reset_index()

    # Standardize output column names
    aggregated.columns = ["product_id", "baseline_sales"]

    return aggregated
