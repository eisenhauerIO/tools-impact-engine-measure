"""
Transforms specific to the Interrupted Time Series model.

These transforms prepare data for ITS analysis by aggregating
time-series data appropriately.
"""

from typing import Any, Dict

import pandas as pd

from ...core import register_transform


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
