"""
Transforms specific to the catalog simulator data source.

These transforms handle the conversion of catalog simulator time-series
metrics into formats suitable for different model types.
"""

from typing import Any, Dict, List

import pandas as pd

from ...core import TransformSchema, register_transform


@register_transform("prepare_simulator_for_approximation")
def prepare_simulator_for_approximation(data: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """Transform catalog simulator time-series metrics to metrics approximation input format.

    Takes time-series metrics from catalog simulator (with quality_score per row)
    and prepares cross-sectional data suitable for MetricsApproximationAdapter.

    The transform splits data by enrichment_start date to determine:
    - quality_before: quality_score before enrichment_start (per product)
    - quality_after: quality_score after enrichment_start (per product)
    - baseline_sales: aggregated revenue before enrichment_start (per product)

    Input DataFrame (time-series from adapter):
        - product_id/product_identifier/asin: Product identifier
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

    # Normalize column names using schema
    df = TransformSchema.from_external(data, "catalog_simulator")

    # Detect product ID column (after normalization)
    id_column = _detect_id_column(df, source="catalog_simulator")

    # Validate required columns after normalization
    required_cols = ["date", "quality_score", baseline_metric]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Data must contain columns: {missing_cols}. "
            f"Available after normalization: {list(df.columns)}"
        )

    # Ensure date column is datetime (df is already a copy from from_external)
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


def _detect_id_column(df: pd.DataFrame, source: str = "catalog_simulator") -> str:
    """Auto-detect product ID column in DataFrame using schema mappings.

    Args:
        df: DataFrame to inspect for ID column.
        source: Source system name for schema lookup (default: catalog_simulator).

    Returns:
        str: Name of the detected ID column.

    Raises:
        ValueError: If no ID column found.
    """
    # Get all possible ID column names from schema
    standard_id = "product_id"
    possible_columns: List[str] = [standard_id]

    # Add external column names from mappings
    if source in TransformSchema.mappings:
        for ext_col, std_col in TransformSchema.mappings[source].items():
            if std_col == "product_id":
                possible_columns.append(ext_col)

    # Check which column exists
    for col in possible_columns:
        if col in df.columns:
            return col

    raise ValueError(
        f"Data must contain one of: {possible_columns}. " f"Available columns: {list(df.columns)}"
    )
