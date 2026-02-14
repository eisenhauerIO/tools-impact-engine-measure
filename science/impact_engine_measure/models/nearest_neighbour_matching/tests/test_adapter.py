"""Tests for NearestNeighbourMatchingAdapter."""

import numpy as np
import pandas as pd
import pytest

from impact_engine_measure.models.base import ModelResult
from impact_engine_measure.models.conftest import merge_model_params
from impact_engine_measure.models.nearest_neighbour_matching import (
    NearestNeighbourMatchingAdapter,
)


def _make_config(**overrides):
    """Create a minimal valid config for NearestNeighbourMatchingAdapter."""
    config = {
        "treatment_column": "treated",
        "covariate_columns": ["x1"],
        "dependent_variable": "revenue",
        "caliper": 0.2,
        "replace": True,
        "ratio": 1,
        "shuffle": True,
        "random_state": 42,
        "n_jobs": 1,
    }
    config.update(overrides)
    return config


def _make_data(n=200, seed=42):
    """Create a simple dataset with known treatment effect.

    Treatment group has outcome = covariate + 10 (effect = 10).
    Control group has outcome = covariate.
    """
    rng = np.random.default_rng(seed)
    n_half = n // 2
    x1 = rng.normal(50, 10, size=n)
    treated = np.array([1] * n_half + [0] * (n - n_half))
    revenue = x1 + treated * 10 + rng.normal(0, 1, size=n)
    return pd.DataFrame({"treated": treated, "x1": x1, "revenue": revenue})


class TestNearestNeighbourMatchingAdapterConnect:
    """Tests for connect() method."""

    def test_connect_success(self):
        """Test successful model connection."""
        model = NearestNeighbourMatchingAdapter()
        config = _make_config()

        result = model.connect(config)

        assert result is True
        assert model.is_connected is True
        assert model.config["caliper"] == 0.2
        assert model.config["replace"] is True

    def test_connect_with_defaults(self):
        """Test connection uses defaults for optional params."""
        model = NearestNeighbourMatchingAdapter()
        config = {
            "treatment_column": "treated",
            "covariate_columns": ["x1"],
        }

        model.connect(config)

        assert model.config["caliper"] == 0.2
        assert model.config["replace"] is False
        assert model.config["ratio"] == 1
        assert model.config["shuffle"] is True
        assert model.config["dependent_variable"] == "revenue"

    def test_connect_missing_treatment_column(self):
        """Test connection with missing treatment_column."""
        model = NearestNeighbourMatchingAdapter()

        with pytest.raises(ValueError, match="treatment_column is required"):
            model.connect(_make_config(treatment_column=None))

    def test_connect_missing_covariate_columns(self):
        """Test connection with missing covariate_columns."""
        model = NearestNeighbourMatchingAdapter()

        with pytest.raises(ValueError, match="covariate_columns is required"):
            model.connect(_make_config(covariate_columns=None))

    def test_connect_invalid_caliper(self):
        """Test connection with invalid caliper."""
        model = NearestNeighbourMatchingAdapter()

        with pytest.raises(ValueError, match="caliper must be a positive number"):
            model.connect(_make_config(caliper=-0.1))

    def test_connect_invalid_ratio(self):
        """Test connection with invalid ratio."""
        model = NearestNeighbourMatchingAdapter()

        with pytest.raises(ValueError, match="ratio must be a positive integer"):
            model.connect(_make_config(ratio=0))

    def test_connect_string_covariate_columns(self):
        """Test that a single covariate string is converted to list."""
        model = NearestNeighbourMatchingAdapter()
        model.connect(_make_config(covariate_columns="x1"))

        assert model.config["covariate_columns"] == ["x1"]

    def test_connect_with_merge_model_params(self):
        """Test connection using merge_model_params for defaults."""
        model = NearestNeighbourMatchingAdapter()
        config = merge_model_params(
            {
                "treatment_column": "treated",
                "covariate_columns": ["x1"],
                "caliper": 0.5,
            }
        )

        result = model.connect(config)

        assert result is True
        assert model.config["caliper"] == 0.5


class TestNearestNeighbourMatchingAdapterValidateParams:
    """Tests for validate_params() method."""

    def test_validate_params_valid(self):
        """Test validate_params with valid params."""
        model = NearestNeighbourMatchingAdapter()

        # Should not raise
        model.validate_params({"treatment_column": "treated", "covariate_columns": ["x1"]})

    def test_validate_params_missing_treatment_column(self):
        """Test validate_params with missing treatment_column."""
        model = NearestNeighbourMatchingAdapter()

        with pytest.raises(ValueError, match="treatment_column is required"):
            model.validate_params({"covariate_columns": ["x1"]})

    def test_validate_params_missing_covariate_columns(self):
        """Test validate_params with missing covariate_columns."""
        model = NearestNeighbourMatchingAdapter()

        with pytest.raises(ValueError, match="covariate_columns is required"):
            model.validate_params({"treatment_column": "treated"})


class TestNearestNeighbourMatchingAdapterFit:
    """Tests for fit() method."""

    def test_fit_not_connected(self):
        """Test fitting without connection."""
        model = NearestNeighbourMatchingAdapter()
        data = _make_data()

        with pytest.raises(ConnectionError, match="Model not connected"):
            model.fit(data)

    def test_fit_returns_model_result(self):
        """Test that fit returns ModelResult."""
        model = NearestNeighbourMatchingAdapter()
        model.connect(_make_config())

        data = _make_data()
        result = model.fit(data)

        assert isinstance(result, ModelResult)
        assert result.model_type == "nearest_neighbour_matching"

    def test_fit_result_data_structure(self):
        """Test that fit returns ModelResult with standardized three-key structure."""
        model = NearestNeighbourMatchingAdapter()
        model.connect(_make_config())

        data = _make_data()
        result = model.fit(data)

        assert "model_params" in result.data
        assert "impact_estimates" in result.data
        assert "model_summary" in result.data
        assert result.data["model_params"]["dependent_variable"] == "revenue"

    def test_fit_impact_estimates_structure(self):
        """Test that impact_estimates has correct keys."""
        model = NearestNeighbourMatchingAdapter()
        model.connect(_make_config())

        data = _make_data()
        result = model.fit(data)
        estimates = result.data["impact_estimates"]

        assert "att" in estimates
        assert "atc" in estimates
        assert "ate" in estimates
        assert "att_se" in estimates
        assert "atc_se" in estimates
        assert isinstance(estimates["att"], float)
        assert isinstance(estimates["atc"], float)
        assert isinstance(estimates["ate"], float)
        assert isinstance(estimates["att_se"], float)
        assert isinstance(estimates["atc_se"], float)

    def test_fit_model_summary_structure(self):
        """Test that model_summary has correct keys."""
        model = NearestNeighbourMatchingAdapter()
        model.connect(_make_config())

        data = _make_data(n=200)
        result = model.fit(data)
        summary = result.data["model_summary"]

        assert summary["n_observations"] == 200
        assert summary["n_treated"] == 100
        assert summary["n_control"] == 100
        assert "n_matched_att" in summary
        assert "n_matched_atc" in summary
        assert summary["caliper"] == 0.2
        assert summary["replace"] is True
        assert summary["ratio"] == 1

    def test_fit_known_effect(self):
        """Test that estimated ATT is close to true effect.

        True effect is 10 (treated outcome = covariate + 10).
        With enough data and correct matching, estimate should be close.
        """
        model = NearestNeighbourMatchingAdapter()
        model.connect(_make_config())

        data = _make_data(n=500, seed=123)
        result = model.fit(data)
        att = result.data["impact_estimates"]["att"]

        assert abs(att - 10.0) < 2.0, f"Expected ATT ~10, got {att}"

    def test_fit_ate_is_weighted_combination(self):
        """Test that ATE = ATT * (n_t/n) + ATC * (n_c/n)."""
        model = NearestNeighbourMatchingAdapter()
        model.connect(_make_config())

        data = _make_data(n=200, seed=99)
        result = model.fit(data)
        estimates = result.data["impact_estimates"]
        summary = result.data["model_summary"]

        n_t = summary["n_treated"]
        n_c = summary["n_control"]
        n = summary["n_observations"]

        expected_ate = estimates["att"] * (n_t / n) + estimates["atc"] * (n_c / n)
        assert abs(estimates["ate"] - expected_ate) < 1e-10

    def test_fit_returns_artifacts(self):
        """Test that fit returns matching artifacts."""
        model = NearestNeighbourMatchingAdapter()
        model.connect(_make_config())

        data = _make_data()
        result = model.fit(data)

        assert "matched_data_att" in result.artifacts
        assert "balance_before" in result.artifacts
        assert "balance_after" in result.artifacts
        assert isinstance(result.artifacts["matched_data_att"], pd.DataFrame)
        assert isinstance(result.artifacts["balance_before"], pd.DataFrame)
        assert isinstance(result.artifacts["balance_after"], pd.DataFrame)

    def test_fit_multiple_covariates(self):
        """Test fitting with multiple covariates (requires replace=True)."""
        rng = np.random.default_rng(42)
        n = 300
        x1 = rng.normal(50, 10, size=n)
        x2 = rng.normal(100, 20, size=n)
        treated = np.array([1] * (n // 2) + [0] * (n // 2))
        revenue = x1 + 0.5 * x2 + treated * 5 + rng.normal(0, 1, size=n)
        data = pd.DataFrame({"treated": treated, "x1": x1, "x2": x2, "revenue": revenue})

        model = NearestNeighbourMatchingAdapter()
        model.connect(_make_config(covariate_columns=["x1", "x2"], replace=True))

        result = model.fit(data)
        att = result.data["impact_estimates"]["att"]
        assert abs(att - 5.0) < 3.0, f"Expected ATT ~5, got {att}"


class TestNearestNeighbourMatchingAdapterValidateData:
    """Tests for validate_data() method."""

    def test_valid_data(self):
        """Test validation with valid data."""
        model = NearestNeighbourMatchingAdapter()
        model.connect(_make_config())

        data = _make_data()
        assert model.validate_data(data) is True

    def test_empty_dataframe(self):
        """Test validation with empty DataFrame."""
        model = NearestNeighbourMatchingAdapter()
        model.connect(_make_config())

        assert model.validate_data(pd.DataFrame()) is False

    def test_missing_columns(self):
        """Test validation with missing required columns."""
        model = NearestNeighbourMatchingAdapter()
        model.connect(_make_config())

        data = pd.DataFrame({"revenue": [1, 2, 3]})
        assert model.validate_data(data) is False


class TestNearestNeighbourMatchingAdapterGetRequiredColumns:
    """Tests for get_required_columns() method."""

    def test_required_columns(self):
        """Test getting required columns."""
        model = NearestNeighbourMatchingAdapter()
        model.connect(_make_config(covariate_columns=["x1", "x2"]))

        columns = model.get_required_columns()

        assert "treated" in columns
        assert "x1" in columns
        assert "x2" in columns

    def test_required_columns_not_connected(self):
        """Test getting required columns before connect."""
        model = NearestNeighbourMatchingAdapter()

        assert model.get_required_columns() == []


class TestNearestNeighbourMatchingGetFitParams:
    """Tests for get_fit_params() method."""

    def test_only_dependent_variable_passes_through(self):
        """Verify only dependent_variable passes through."""
        model = NearestNeighbourMatchingAdapter()
        params = {
            "dependent_variable": "revenue",
            "treatment_column": "treated",
            "covariate_columns": ["x1"],
            "caliper": 0.2,
            "replace": True,
            "ratio": 1,
            "intervention_date": "2024-01-15",
        }

        filtered = model.get_fit_params(params)

        assert filtered == {"dependent_variable": "revenue"}

    def test_irrelevant_params_excluded(self):
        """Verify all non-fit params are excluded."""
        model = NearestNeighbourMatchingAdapter()
        params = {
            "treatment_column": "treated",
            "covariate_columns": ["x1"],
            "caliper": 0.2,
        }

        filtered = model.get_fit_params(params)

        assert filtered == {}

    def test_empty_params(self):
        """Verify empty params returns empty dict."""
        model = NearestNeighbourMatchingAdapter()

        assert model.get_fit_params({}) == {}
