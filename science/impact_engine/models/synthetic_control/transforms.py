"""Transforms specific to the Synthetic Control model."""

from typing import Any, Dict

import pandas as pd

from ...core import register_transform


@register_transform("prepare_for_synthetic_control")
def prepare_for_synthetic_control(data: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """Add treatment column from enriched status and enrichment start date.

    For each row, treatment = 1 when the product is enriched AND the date is
    on or after ``enrichment_start``.  Otherwise treatment = 0.

    Args:
        data: Long-format panel DataFrame with ``enriched`` and ``date`` columns.
        params: Configuration parameters:
            - enrichment_start (str): Date when enrichment started (YYYY-MM-DD).
              Auto-injected from ENRICHMENT.PARAMS by validation.py.

    Returns:
        pd.DataFrame: Data with an added ``treatment`` column.
    """
    result = data.copy()
    enrichment_start = params.get("enrichment_start")

    if "enriched" in result.columns and enrichment_start:
        enrichment_date = pd.to_datetime(enrichment_start)
        result["date"] = pd.to_datetime(result["date"])
        result["treatment"] = 0
        mask = result["enriched"].astype(bool) & (result["date"] >= enrichment_date)
        result.loc[mask, "treatment"] = 1
    else:
        result["treatment"] = 0

    return result
