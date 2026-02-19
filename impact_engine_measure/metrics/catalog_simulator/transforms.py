"""
Transforms specific to the catalog simulator data source.

These transforms handle the conversion of catalog simulator time-series
metrics into formats suitable for different model types.
"""

from typing import Any, Dict

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
        - product_id/product_identifier: Product identifier
        - date: Date of metrics
        - quality_score: Quality score at that time point
        - revenue: Sales revenue

    Output (for metrics approximation):
        - product_id: Product identifier
        - quality_before: Quality score before enrichment_start
        - quality_after: Quality score after enrichment_start
        - baseline_sales: Aggregated revenue before enrichment_start
        - All other columns: Preserved (first value per product) for attribute-based conditioning

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

    # Detect product ID column using schema (after normalization)
    id_column = TransformSchema.get_column(df, "product_id")
    if not id_column:
        raise ValueError(
            f"Data must contain product_id or alias (product_identifier). " f"Available columns: {list(df.columns)}"
        )

    # Validate required columns after normalization
    required_cols = ["date", "quality_score", baseline_metric]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Data must contain columns: {missing_cols}. " f"Available after normalization: {list(df.columns)}"
        )

    # Ensure date column is datetime (df is already a copy from from_external)
    df["date"] = pd.to_datetime(df["date"])
    enrichment_date = pd.to_datetime(enrichment_start)

    # Split into before and after periods
    before_df = df[df["date"] < enrichment_date]
    after_df = df[df["date"] >= enrichment_date]

    # Identify attribute columns (static per product, not aggregated)
    aggregated_cols = {"date", "quality_score", baseline_metric, id_column}
    attribute_cols = [col for col in df.columns if col not in aggregated_cols]

    # Build result with single groupby per period
    def aggregate_period(period_df, fallback_df):
        """Aggregate a period, falling back if empty."""
        source = period_df if len(period_df) > 0 else fallback_df
        agg_dict = {
            "quality_score": "first",
            baseline_metric: "sum",
        }
        # Add attribute columns (take first value)
        for col in attribute_cols:
            if col in source.columns:
                agg_dict[col] = "first"
        return source.groupby(id_column).agg(agg_dict).reset_index()

    before_agg = aggregate_period(before_df, df)
    after_agg = aggregate_period(after_df, before_df)

    # Build result
    result = pd.DataFrame(
        {
            "product_id": before_agg[id_column],
            "quality_before": before_agg["quality_score"],
            "quality_after": after_agg["quality_score"],
            "baseline_sales": before_agg[baseline_metric],
        }
    )

    # Add attribute columns
    for col in attribute_cols:
        if col in before_agg.columns:
            result[col] = before_agg[col]

    return result
