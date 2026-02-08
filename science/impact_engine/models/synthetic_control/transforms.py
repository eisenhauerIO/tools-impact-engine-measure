"""Transforms specific to the Synthetic Control model.

These transforms prepare panel data for CausalPy's SyntheticControl API
by pivoting from long to wide format.
"""

from typing import Any, Dict, List, Tuple

import pandas as pd

from ...core import register_transform


def pivot_to_wide(
    data: pd.DataFrame,
    unit_column: str,
    time_column: str,
    outcome_column: str,
    treatment_column: str = "treatment",
) -> Tuple[pd.DataFrame, List[str], List[str]]:
    """Pivot panel data from long to wide format for CausalPy.

    CausalPy's SyntheticControl expects wide-format data where each column
    is a unit and each row is a time period. This function converts standard
    panel (long) format to that layout and identifies treated vs control units.

    Args:
        data: Long-format panel DataFrame with columns for unit, time,
            outcome, and treatment indicator.
        unit_column: Column identifying units (e.g., "unit_id").
        time_column: Column identifying time periods (e.g., "date").
        outcome_column: Column with the outcome variable (e.g., "revenue").
        treatment_column: Column with treatment indicator (0/1). Default: "treatment".

    Returns:
        Tuple of:
            - wide_df: DataFrame with time as index, one column per unit.
            - treated_units: List of treated unit names.
            - control_units: List of control unit names.

    Raises:
        ValueError: If required columns are missing or no treated/control units found.
    """
    required = [unit_column, time_column, outcome_column, treatment_column]
    missing = [col for col in required if col not in data.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Identify treated and control units
    # A unit is treated if it has any treatment_column == 1
    unit_treatment = data.groupby(unit_column)[treatment_column].max()
    treated_units = unit_treatment[unit_treatment > 0].index.tolist()
    control_units = unit_treatment[unit_treatment == 0].index.tolist()

    if not treated_units:
        raise ValueError("No treated units found in data")
    if not control_units:
        raise ValueError("No control units found in data")

    # Pivot to wide format: index=time, columns=unit, values=outcome
    wide_df = data.pivot(index=time_column, columns=unit_column, values=outcome_column)

    # Convert unit identifiers to strings (CausalPy expects string column names)
    wide_df.columns = [str(c) for c in wide_df.columns]
    treated_units = [str(u) for u in treated_units]
    control_units = [str(u) for u in control_units]

    return wide_df, treated_units, control_units


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
