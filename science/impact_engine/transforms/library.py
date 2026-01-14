"""
Library of transform functions for data processing.

These functions transform raw business metrics into formats suitable
for different model types (ITS, metrics approximation, etc.).
"""

from typing import Any, Dict, Optional

import pandas as pd

from ..core.contracts import MetricsSchema, ProductSchema, Schema
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

    Uses schema-based column resolution to decouple from specific adapter column names.

    Args:
        data: Input DataFrame with 'product_id' column and metrics.
        params: Configuration parameters:
            - baseline_metric (str): The metric to aggregate as baseline (default: "revenue").
            - schema (Schema): Optional schema for column resolution. Defaults to ProductSchema.

    Returns:
        pd.DataFrame: Cross-sectional data with columns:
            - product_id: Product identifier
            - baseline_sales: Aggregated baseline metric per product

    Raises:
        ValueError: If required columns are missing.
    """
    baseline_metric = params.get("baseline_metric", "revenue")
    schema = params.get("schema", ProductSchema)

    # Use schema-based resolution to find the ID column
    id_column = _detect_id_column(data, schema)

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


@register_transform("prepare_simulator_for_approximation")
def prepare_simulator_for_approximation(
    data: pd.DataFrame, params: Dict[str, Any]
) -> pd.DataFrame:
    """Transform catalog simulator time-series metrics to metrics approximation input format.

    Takes time-series metrics from catalog simulator (with quality_score per row)
    and prepares cross-sectional data suitable for MetricsApproximationAdapter.

    Uses schema-based column resolution to decouple from specific adapter column names,
    enabling the transform to work with data from any source that conforms to the schema.

    The transform splits data by enrichment_start date to determine:
    - quality_before: quality_score before enrichment_start (per product)
    - quality_after: quality_score after enrichment_start (per product)
    - baseline_sales: aggregated revenue before enrichment_start (per product)

    Input DataFrame (time-series from adapter):
        - product_id/product_identifier/asin: Product identifier (resolved via schema)
        - date: Date of metrics
        - quality_score: Quality score at that time point
        - revenue: Sales revenue

    Output (for metrics approximation):
        - product_id: Product identifier
        - quality_before: Quality score before enrichment_start
        - quality_after: Quality score after enrichment_start
        - baseline_sales: Aggregated revenue before enrichment_start

    Args:
        data: Time-series DataFrame with quality_score per row.
        params: Configuration parameters:
            - enrichment_start (str): Date when enrichment started (REQUIRED, format: YYYY-MM-DD)
            - baseline_metric (str): Column to aggregate as baseline. Default: "revenue"
            - schema (Schema): Optional schema for column resolution. Defaults to MetricsSchema.
            - source (str): Optional source type hint for schema resolution (e.g., "catalog_simulator")

    Returns:
        pd.DataFrame: Cross-sectional data ready for MetricsApproximationAdapter.

    Raises:
        ValueError: If required columns or params are missing.
    """
    # Validate input
    if not isinstance(data, pd.DataFrame):
        raise ValueError("prepare_simulator_for_approximation requires DataFrame input")

    # Get required param
    enrichment_start = params.get("enrichment_start")
    if not enrichment_start:
        raise ValueError("prepare_simulator_for_approximation requires 'enrichment_start' param")

    baseline_metric = params.get("baseline_metric", "revenue")
    schema = params.get("schema", MetricsSchema)
    source = params.get("source")

    # Use schema-based resolution to detect product ID column
    id_column = _detect_id_column(data, schema)

    # Validate required columns
    if "date" not in data.columns:
        raise ValueError("Data must contain 'date' column")
    if "quality_score" not in data.columns:
        raise ValueError("Data must contain 'quality_score' column")
    if baseline_metric not in data.columns:
        raise ValueError(f"Data must contain '{baseline_metric}' column")

    # Ensure date column is datetime
    df = data.copy()
    df["date"] = pd.to_datetime(df["date"])
    enrichment_date = pd.to_datetime(enrichment_start)

    # Split into before and after periods
    before_df = df[df["date"] < enrichment_date]
    after_df = df[df["date"] >= enrichment_date]

    # Extract quality_before (quality_score from before period, per product)
    if len(before_df) > 0:
        quality_before = before_df.groupby(id_column)["quality_score"].first().reset_index()
    else:
        # If no before data, use first available quality_score
        quality_before = df.groupby(id_column)["quality_score"].first().reset_index()
    quality_before.columns = ["product_id", "quality_before"]

    # Extract quality_after (quality_score from after period, per product)
    if len(after_df) > 0:
        quality_after = after_df.groupby(id_column)["quality_score"].first().reset_index()
    else:
        # If no after data, use quality_before
        quality_after = quality_before.copy()
        quality_after.columns = ["product_id", "quality_after"]
    if "quality_after" not in quality_after.columns:
        quality_after.columns = ["product_id", "quality_after"]

    # Aggregate baseline_sales from before period
    if len(before_df) > 0:
        baseline_agg = before_df.groupby(id_column)[baseline_metric].sum().reset_index()
    else:
        # If no before data, use all data
        baseline_agg = df.groupby(id_column)[baseline_metric].sum().reset_index()
    baseline_agg.columns = ["product_id", "baseline_sales"]

    # Merge all components
    result = quality_before.merge(quality_after, on="product_id", how="inner")
    result = result.merge(baseline_agg, on="product_id", how="inner")

    # Reorder columns
    return result[["product_id", "quality_before", "quality_after", "baseline_sales"]]


def _detect_id_column(df: pd.DataFrame, schema: Optional[Schema] = None) -> str:
    """Auto-detect product ID column in DataFrame using schema-based resolution.

    This function decouples transforms from specific adapter column names by using
    the Schema's resolve_column method to find the actual column name.

    Args:
        df: DataFrame to search for the ID column
        schema: Optional Schema to use for resolution. Defaults to ProductSchema.

    Returns:
        str: The actual column name found in the DataFrame

    Raises:
        ValueError: If no matching column is found
    """
    if schema is None:
        schema = ProductSchema

    try:
        return schema.resolve_column(df, "product_id")
    except ValueError:
        # Fallback to legacy detection for backward compatibility
        for col in ["product_identifier", "product_id", "asin"]:
            if col in df.columns:
                return col
        raise ValueError(
            "Data must contain 'product_identifier', 'product_id', or 'asin' column"
        )
