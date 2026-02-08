"""Tests for SubclassificationAdapter."""

import numpy as np
import pandas as pd
import pytest

from impact_engine.models.base import ModelResult
from impact_engine.models.conftest import merge_model_params
from impact_engine.models.subclassification import SubclassificationAdapter


def _make_config(**overrides):
    """Create a minimal valid config for SubclassificationAdapter."""
    config = {
        "n_strata": 5,
        "estimand": "att",
        "treatment_column": "treated",
        "covariate_columns": ["x1"],
        "dependent_variable": "revenue",
    }
    config.update(overrides)
    return config


def _make_data(n=100, seed=42):
    """Create a simple dataset with known treatment effect.

    Treatment group has outcome = covariate + 10 (effect = 10).
    Control group has outcome = covariate.
    """
    rng = np.random.default_rng(seed)
    x1 = rng.normal(50, 10, size=n)
    treated = np.array([1] * (n // 2) + [0] * (n // 2))
    revenue = x1 + treated * 10 + rng.normal(0, 1, size=n)
    return pd.DataFrame({"treated": treated, "x1": x1, "revenue": revenue})


class TestSubclassificationAdapterConnect:
    """Tests for connect() method."""

    def test_connect_success(self):
        """Test successful model connection."""
        model = SubclassificationAdapter()
        config = _make_config()

        result = model.connect(config)

        assert result is True
        assert model.is_connected is True
        assert model.config["n_strata"] == 5
        assert model.config["estimand"] == "att"

    def test_connect_with_defaults(self):
        """Test connection uses defaults for optional params."""
        model = SubclassificationAdapter()
        config = {
            "treatment_column": "treated",
            "covariate_columns": ["x1"],
        }

        model.connect(config)

        assert model.config["n_strata"] == 5
        assert model.config["estimand"] == "att"
        assert model.config["dependent_variable"] == "revenue"

    def test_connect_invalid_n_strata(self):
        """Test connection with invalid n_strata."""
        model = SubclassificationAdapter()

        with pytest.raises(ValueError, match="n_strata must be a positive integer"):
            model.connect(_make_config(n_strata=-1))

    def test_connect_invalid_estimand(self):
        """Test connection with invalid estimand."""
        model = SubclassificationAdapter()

        with pytest.raises(ValueError, match="estimand must be 'att' or 'ate'"):
            model.connect(_make_config(estimand="invalid"))

    def test_connect_missing_treatment_column(self):
        """Test connection with missing treatment_column."""
        model = SubclassificationAdapter()

        with pytest.raises(ValueError, match="treatment_column is required"):
            model.connect(_make_config(treatment_column=None))

    def test_connect_missing_covariate_columns(self):
        """Test connection with missing covariate_columns."""
        model = SubclassificationAdapter()

        with pytest.raises(ValueError, match="covariate_columns is required"):
            model.connect(_make_config(covariate_columns=None))

    def test_connect_string_covariate_columns(self):
        """Test that a single covariate string is converted to list."""
        model = SubclassificationAdapter()
        model.connect(_make_config(covariate_columns="x1"))

        assert model.config["covariate_columns"] == ["x1"]

    def test_connect_with_merge_model_params(self):
        """Test connection using merge_model_params for defaults."""
        model = SubclassificationAdapter()
        config = merge_model_params(
            {
                "treatment_column": "treated",
                "covariate_columns": ["x1"],
                "n_strata": 3,
                "estimand": "ate",
            }
        )

        result = model.connect(config)

        assert result is True
        assert model.config["n_strata"] == 3
        assert model.config["estimand"] == "ate"


class TestSubclassificationAdapterValidateParams:
    """Tests for validate_params() method."""

    def test_validate_params_valid(self):
        """Test validate_params with valid params."""
        model = SubclassificationAdapter()
        model.connect(_make_config())

        # Should not raise
        model.validate_params({"treatment_column": "treated", "covariate_columns": ["x1"]})

    def test_validate_params_missing_treatment_column(self):
        """Test validate_params with missing treatment_column."""
        model = SubclassificationAdapter()

        with pytest.raises(ValueError, match="treatment_column is required"):
            model.validate_params({"covariate_columns": ["x1"]})

    def test_validate_params_missing_covariate_columns(self):
        """Test validate_params with missing covariate_columns."""
        model = SubclassificationAdapter()

        with pytest.raises(ValueError, match="covariate_columns is required"):
            model.validate_params({"treatment_column": "treated"})


class TestSubclassificationAdapterFit:
    """Tests for fit() method."""

    def test_fit_not_connected(self):
        """Test fitting without connection."""
        model = SubclassificationAdapter()
        data = _make_data()

        with pytest.raises(ConnectionError, match="Model not connected"):
            model.fit(data, treatment_column="treated", covariate_columns=["x1"])

    def test_fit_returns_model_result(self):
        """Test that fit returns ModelResult."""
        model = SubclassificationAdapter()
        model.connect(_make_config())

        data = _make_data()
        result = model.fit(data)

        assert isinstance(result, ModelResult)
        assert result.model_type == "subclassification"

    def test_fit_result_data_structure(self):
        """Test that fit returns ModelResult with correct data structure."""
        model = SubclassificationAdapter()
        model.connect(_make_config())

        data = _make_data()
        result = model.fit(data)

        assert "dependent_variable" in result.data
        assert "impact_estimates" in result.data
        assert "model_summary" in result.data

    def test_fit_impact_estimates_structure(self):
        """Test that impact_estimates has correct keys."""
        model = SubclassificationAdapter()
        model.connect(_make_config())

        data = _make_data()
        result = model.fit(data)
        estimates = result.data["impact_estimates"]

        assert "treatment_effect" in estimates
        assert "n_strata" in estimates
        assert "n_strata_dropped" in estimates
        assert isinstance(estimates["treatment_effect"], float)
        assert isinstance(estimates["n_strata"], int)
        assert isinstance(estimates["n_strata_dropped"], int)

    def test_fit_model_summary_structure(self):
        """Test that model_summary has correct keys."""
        model = SubclassificationAdapter()
        model.connect(_make_config())

        data = _make_data(n=100)
        result = model.fit(data)
        summary = result.data["model_summary"]

        assert summary["n_observations"] == 100
        assert summary["n_treated"] == 50
        assert summary["n_control"] == 50
        assert summary["estimand"] == "att"

    def test_fit_known_effect(self):
        """Test that estimated treatment effect is close to true effect.

        True effect is 10 (treated outcome = covariate + 10).
        With enough data and correct stratification, estimate should be close.
        """
        model = SubclassificationAdapter()
        model.connect(_make_config(n_strata=10))

        data = _make_data(n=1000, seed=123)
        result = model.fit(data)
        effect = result.data["impact_estimates"]["treatment_effect"]

        assert abs(effect - 10.0) < 1.0, f"Expected ~10, got {effect}"

    def test_fit_ate_estimand(self):
        """Test fitting with ATE estimand."""
        model = SubclassificationAdapter()
        model.connect(_make_config(estimand="ate"))

        data = _make_data(n=500, seed=99)
        result = model.fit(data)
        summary = result.data["model_summary"]

        assert summary["estimand"] == "ate"
        effect = result.data["impact_estimates"]["treatment_effect"]
        assert abs(effect - 10.0) < 2.0, f"Expected ~10, got {effect}"

    def test_fit_multiple_covariates(self):
        """Test fitting with multiple covariates."""
        rng = np.random.default_rng(42)
        n = 200
        x1 = rng.normal(50, 10, size=n)
        x2 = rng.normal(100, 20, size=n)
        treated = np.array([1] * (n // 2) + [0] * (n // 2))
        revenue = x1 + 0.5 * x2 + treated * 5 + rng.normal(0, 1, size=n)
        data = pd.DataFrame({"treated": treated, "x1": x1, "x2": x2, "revenue": revenue})

        model = SubclassificationAdapter()
        model.connect(_make_config(covariate_columns=["x1", "x2"]))

        result = model.fit(data)
        effect = result.data["impact_estimates"]["treatment_effect"]
        assert abs(effect - 5.0) < 2.0, f"Expected ~5, got {effect}"

    def test_fit_returns_stratum_details_artifact(self):
        """Test that fit returns stratum_details in artifacts."""
        model = SubclassificationAdapter()
        model.connect(_make_config())

        data = _make_data()

        result = model.fit(data)

        assert "stratum_details" in result.artifacts
        assert isinstance(result.artifacts["stratum_details"], pd.DataFrame)

    def test_fit_no_common_support_all_dropped(self):
        """Test that all strata dropped returns zero-effect result."""
        # All treated in one region, all control in another → no overlap
        data = pd.DataFrame(
            {
                "treated": [1, 1, 1, 1, 0, 0, 0, 0],
                "x1": [1, 2, 3, 4, 100, 101, 102, 103],
                "revenue": [10, 11, 12, 13, 20, 21, 22, 23],
            }
        )

        model = SubclassificationAdapter()
        model.connect(_make_config(n_strata=4))

        result = model.fit(data)

        assert result.data["impact_estimates"]["treatment_effect"] == 0.0
        assert result.data["impact_estimates"]["n_strata"] == 0

    def test_fit_qcut_duplicate_edges(self):
        """Test handling of pd.qcut with duplicate bin edges."""
        # Many identical values → qcut must use duplicates='drop'
        data = pd.DataFrame(
            {
                "treated": [1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
                "x1": [5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
                "revenue": [15, 16, 17, 18, 19, 10, 11, 12, 13, 14],
            }
        )

        model = SubclassificationAdapter()
        model.connect(_make_config(n_strata=5))

        # Should not raise despite duplicate edges
        result = model.fit(data)
        assert isinstance(result, ModelResult)
        # Single effective stratum
        assert result.data["impact_estimates"]["n_strata"] == 1


class TestSubclassificationAdapterValidateData:
    """Tests for validate_data() method."""

    def test_valid_data(self):
        """Test validation with valid data."""
        model = SubclassificationAdapter()
        model.connect(_make_config())

        data = _make_data()
        assert model.validate_data(data) is True

    def test_empty_dataframe(self):
        """Test validation with empty DataFrame."""
        model = SubclassificationAdapter()
        model.connect(_make_config())

        assert model.validate_data(pd.DataFrame()) is False

    def test_missing_columns(self):
        """Test validation with missing required columns."""
        model = SubclassificationAdapter()
        model.connect(_make_config())

        data = pd.DataFrame({"revenue": [1, 2, 3]})
        assert model.validate_data(data) is False


class TestSubclassificationAdapterGetRequiredColumns:
    """Tests for get_required_columns() method."""

    def test_required_columns(self):
        """Test getting required columns."""
        model = SubclassificationAdapter()
        model.connect(_make_config(covariate_columns=["x1", "x2"]))

        columns = model.get_required_columns()

        assert "treated" in columns
        assert "x1" in columns
        assert "x2" in columns

    def test_required_columns_not_connected(self):
        """Test getting required columns before connect."""
        model = SubclassificationAdapter()

        assert model.get_required_columns() == []


class TestSubclassificationGetFitParams:
    """Tests for get_fit_params() method."""

    def test_only_dependent_variable_passes_through(self):
        """Verify only dependent_variable passes through."""
        model = SubclassificationAdapter()
        params = {
            "dependent_variable": "revenue",
            "treatment_column": "treated",
            "covariate_columns": ["x1"],
            "n_strata": 5,
            "estimand": "att",
            "intervention_date": "2024-01-15",
        }

        filtered = model.get_fit_params(params)

        assert filtered == {"dependent_variable": "revenue"}

    def test_irrelevant_params_excluded(self):
        """Verify all non-fit params are excluded."""
        model = SubclassificationAdapter()
        params = {
            "treatment_column": "treated",
            "covariate_columns": ["x1"],
            "n_strata": 5,
        }

        filtered = model.get_fit_params(params)

        assert filtered == {}

    def test_empty_params(self):
        """Verify empty params returns empty dict."""
        model = SubclassificationAdapter()

        assert model.get_fit_params({}) == {}
