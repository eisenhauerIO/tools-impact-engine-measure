"""
Library of transform functions for data processing.

These functions transform raw business metrics into formats suitable
for different model types (ITS, metrics approximation, etc.).
"""

from typing import Any, Dict

import pandas as pd

from .registry import register_transform


@register_transform("aggregate_by_date")
def aggregate_by_date(data: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """Aggregate data by date for time series analysis.

    This transform is used by Interrupted Time Series (ITS) models.
    It groups data by date and sums numeric columns.

    Args:
        data: Input DataFrame with 'date' column and numeric metrics.
        params: Configuration parameters:
            - metric (str): The primary metric column name (default: "revenue").
                           All numeric columns are summed, but this validates the metric exists.

    Returns:
        pd.DataFrame: Aggregated data with one row per date.

    Raises:
        ValueError: If 'date' column is missing or metric column doesn't exist.
    """
    metric = params.get("metric", "revenue")

    if "date" not in data.columns:
        raise ValueError("Data must contain 'date' column for aggregate_by_date transform")

    if metric not in data.columns:
        raise ValueError(f"Data must contain metric column '{metric}'")

    # Sum all numeric columns, keeping date
    numeric_cols = data.select_dtypes(include=["number"]).columns.tolist()
    aggregated = data.groupby("date")[numeric_cols].sum().reset_index()

    return aggregated


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

    # Handle both 'product_id' and 'asin' column names
    id_column = None
    if "product_id" in data.columns:
        id_column = "product_id"
    elif "asin" in data.columns:
        id_column = "asin"
    else:
        raise ValueError(
            "Data must contain 'product_id' or 'asin' column for aggregate_for_approximation"
        )

    if baseline_metric not in data.columns:
        raise ValueError(f"Data must contain baseline metric column '{baseline_metric}'")

    # Aggregate baseline metric per product
    aggregated = data.groupby(id_column).agg({baseline_metric: "sum"}).reset_index()

    # Standardize output column names
    aggregated.columns = ["product_id", "baseline_sales"]

    return aggregated


@register_transform("passthrough")
def passthrough(data: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """Pass data through unchanged.

    Useful when no transformation is needed but a transform must be specified.

    Args:
        data: Input DataFrame.
        params: Unused parameters.

    Returns:
        pd.DataFrame: The input data unchanged.
    """
    return data
