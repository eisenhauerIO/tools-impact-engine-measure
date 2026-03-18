"""Unit tests for normalize_result covering all 6 model types."""

import pytest

from impact_engine_measure.normalize import normalize_result


def test_normalize_experiment():
    result = {
        "model_type": "experiment",
        "data": {
            "model_params": {"formula": "revenue ~ enriched + price"},
            "impact_estimates": {
                "params": {"enriched[T.True]": 5.0, "price": 0.3},
                "conf_int": {"enriched[T.True]": [2.0, 8.0], "price": [0.1, 0.5]},
                "pvalues": {"enriched[T.True]": 0.01, "price": 0.05},
            },
            "model_summary": {"nobs": 200},
        },
    }
    normalized = normalize_result(result)
    assert normalized["effect_estimate"] == 5.0
    assert normalized["ci_lower"] == 2.0
    assert normalized["ci_upper"] == 8.0
    assert normalized["p_value"] == 0.01
    assert normalized["sample_size"] == 200


def test_normalize_synthetic_control():
    result = {
        "model_type": "synthetic_control",
        "data": {
            "impact_estimates": {"att": 0.05, "ci_lower": 0.01, "ci_upper": 0.09},
            "model_summary": {"n_post_periods": 30},
        },
    }
    normalized = normalize_result(result)
    assert normalized["effect_estimate"] == 0.05
    assert normalized["ci_lower"] == 0.01
    assert normalized["ci_upper"] == 0.09
    assert normalized["p_value"] is None
    assert normalized["sample_size"] == 30


def test_normalize_nearest_neighbour():
    result = {
        "model_type": "nearest_neighbour_matching",
        "data": {
            "impact_estimates": {"att": 10.0, "att_se": 2.0},
            "model_summary": {"n_observations": 500},
        },
    }
    normalized = normalize_result(result)
    assert normalized["effect_estimate"] == 10.0
    assert normalized["ci_lower"] == pytest.approx(10.0 - 1.96 * 2.0)
    assert normalized["ci_upper"] == pytest.approx(10.0 + 1.96 * 2.0)
    assert normalized["p_value"] is None
    assert normalized["sample_size"] == 500


def test_normalize_interrupted_time_series():
    result = {
        "model_type": "interrupted_time_series",
        "data": {
            "impact_estimates": {"intervention_effect": 3.5},
            "model_summary": {"n_observations": 120},
        },
    }
    normalized = normalize_result(result)
    assert normalized["effect_estimate"] == 3.5
    assert normalized["ci_lower"] == 3.5
    assert normalized["ci_upper"] == 3.5
    assert normalized["p_value"] is None
    assert normalized["sample_size"] == 120


def test_normalize_subclassification():
    result = {
        "model_type": "subclassification",
        "data": {
            "impact_estimates": {"treatment_effect": 7.2},
            "model_summary": {"n_observations": 300},
        },
    }
    normalized = normalize_result(result)
    assert normalized["effect_estimate"] == 7.2
    assert normalized["ci_lower"] == 7.2
    assert normalized["ci_upper"] == 7.2
    assert normalized["p_value"] is None
    assert normalized["sample_size"] == 300


def test_normalize_metrics_approximation():
    result = {
        "model_type": "metrics_approximation",
        "data": {
            "impact_estimates": {"impact": 1.5},
            "model_summary": {"n_products": 50},
        },
    }
    normalized = normalize_result(result)
    assert normalized["effect_estimate"] == 1.5
    assert normalized["ci_lower"] == 1.5
    assert normalized["ci_upper"] == 1.5
    assert normalized["p_value"] is None
    assert normalized["sample_size"] == 50


def test_normalize_unknown_model_raises():
    result = {
        "model_type": "unknown_model",
        "data": {"impact_estimates": {}, "model_summary": {}},
    }
    with pytest.raises(ValueError, match="Unknown model_type"):
        normalize_result(result)
