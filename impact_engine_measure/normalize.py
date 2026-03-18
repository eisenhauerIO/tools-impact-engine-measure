"""Normalize model-specific impact results into a flat estimate dict.

Each measurement model stores results in a different schema inside
``impact_results.json``. This module collapses all schemas into a single
flat dict with five standardized fields, written as ``measure_result.json``
so downstream consumers (orchestrator, allocate) never need to parse
model-specific output.
"""

from __future__ import annotations

from typing import Any

MEASURE_RESULT_FILENAME = "measure_result.json"


def _resolve_param_key(treatment_var: str, params: dict) -> str:
    """Find the statsmodels coefficient key for a treatment variable.

    Statsmodels encodes categoricals as e.g. ``enriched[T.True]``.
    Returns an exact match first, then falls back to prefix matching.

    Parameters
    ----------
    treatment_var : str
        Name of the treatment variable from the formula.
    params : dict
        Coefficient dictionary from the statsmodels result.

    Returns
    -------
    str
        Matching key in ``params``.

    Raises
    ------
    KeyError
        If no matching key is found.
    """
    if treatment_var in params:
        return treatment_var
    matches = [k for k in params if k.startswith(f"{treatment_var}[")]
    if len(matches) == 1:
        return matches[0]
    raise KeyError(f"Treatment variable {treatment_var!r} not found in params: {list(params.keys())}")


def normalize_result(impact_results: dict[str, Any]) -> dict[str, Any]:
    """Extract a flat estimate dict from any model type's impact_results envelope.

    Parameters
    ----------
    impact_results : dict
        Full ``impact_results.json`` content with ``model_type``, ``data``.

    Returns
    -------
    dict
        Flat dict with keys: ``effect_estimate``, ``ci_lower``, ``ci_upper``,
        ``p_value``, ``sample_size``.

    Raises
    ------
    ValueError
        If the model type is unknown.
    """
    model_type = impact_results["model_type"]
    estimates = impact_results["data"]["impact_estimates"]
    summary = impact_results["data"]["model_summary"]

    if model_type == "experiment":
        formula = impact_results["data"]["model_params"]["formula"]
        treatment_var = formula.split("~")[1].strip().split("+")[0].strip()
        key = _resolve_param_key(treatment_var, estimates["params"])
        return {
            "effect_estimate": estimates["params"][key],
            "ci_lower": estimates["conf_int"][key][0],
            "ci_upper": estimates["conf_int"][key][1],
            "p_value": estimates["pvalues"][key],
            "sample_size": int(summary["nobs"]),
        }

    if model_type == "synthetic_control":
        return {
            "effect_estimate": estimates["att"],
            "ci_lower": estimates["ci_lower"],
            "ci_upper": estimates["ci_upper"],
            "p_value": None,
            "sample_size": summary["n_post_periods"],
        }

    if model_type == "nearest_neighbour_matching":
        att = estimates["att"]
        att_se = estimates["att_se"]
        return {
            "effect_estimate": att,
            "ci_lower": att - 1.96 * att_se,
            "ci_upper": att + 1.96 * att_se,
            "p_value": None,
            "sample_size": summary["n_observations"],
        }

    if model_type == "interrupted_time_series":
        effect = estimates["intervention_effect"]
        return {
            "effect_estimate": effect,
            "ci_lower": effect,
            "ci_upper": effect,
            "p_value": None,
            "sample_size": summary["n_observations"],
        }

    if model_type == "subclassification":
        effect = estimates["treatment_effect"]
        return {
            "effect_estimate": effect,
            "ci_lower": effect,
            "ci_upper": effect,
            "p_value": None,
            "sample_size": summary["n_observations"],
        }

    if model_type == "metrics_approximation":
        effect = estimates["impact"]
        return {
            "effect_estimate": effect,
            "ci_lower": effect,
            "ci_upper": effect,
            "p_value": None,
            "sample_size": summary["n_products"],
        }

    raise ValueError(f"Unknown model_type: {model_type!r}")
