"""Tests for SyntheticControlAdapter."""

import numpy as np
import pandas as pd
import pytest

from impact_engine_measure.models.base import ModelResult
from impact_engine_measure.models.conftest import merge_model_params
from impact_engine_measure.models.synthetic_control import SyntheticControlAdapter


def _make_panel_data(n_control=4, n_pre=20, n_post=10, treatment_effect=10.0, seed=42):
    """Create synthetic panel data for SC tests.

    Generates one treated unit and n_control control units. Pre-treatment,
    treated unit tracks the controls. Post-treatment, a constant shift is added.
    """
    rng = np.random.default_rng(seed)
    n_total = n_pre + n_post
    dates = pd.date_range("2024-01-01", periods=n_total, freq="D")

    rows = []
    # Control units: random walk with shared trend
    base_trend = np.cumsum(rng.normal(0, 0.5, n_total)) + 100

    for i in range(n_control):
        unit_values = base_trend + rng.normal(0, 1, n_total)
        for t in range(n_total):
            rows.append(
                {
                    "date": dates[t],
                    "unit_id": f"control_{i}",
                    "outcome": unit_values[t],
                    "treatment": 0,
                }
            )

    # Treated unit: follows trend pre-treatment, shifts post-treatment
    treated_values = base_trend + rng.normal(0, 1, n_total)
    for t in range(n_total):
        is_post = t >= n_pre
        rows.append(
            {
                "date": dates[t],
                "unit_id": "treated",
                "outcome": treated_values[t] + (treatment_effect if is_post else 0),
                "treatment": 1 if is_post else 0,
            }
        )

    return pd.DataFrame(rows)


class TestSyntheticControlAdapterConnect:
    """Tests for connect() method."""

    def test_connect_success(self):
        """Test successful model connection."""
        adapter = SyntheticControlAdapter()

        config = {
            "unit_column": "unit_id",
            "time_column": "date",
            "outcome_column": "revenue",
        }

        result = adapter.connect(config)
        assert result is True
        assert adapter.is_connected is True
        assert adapter.config == config

    def test_connect_defaults(self):
        """Test connect with minimal config uses defaults."""
        adapter = SyntheticControlAdapter()

        config = merge_model_params({"outcome_column": "revenue"})
        result = adapter.connect(config)

        assert result is True
        assert adapter.config["unit_column"] == "unit_id"
        assert adapter.config["time_column"] == "date"

    def test_connect_invalid_unit_column(self):
        """Test connection with invalid unit_column."""
        adapter = SyntheticControlAdapter()

        with pytest.raises(ValueError, match="unit_column must be a string"):
            adapter.connect({"unit_column": 123, "outcome_column": "revenue"})

    def test_connect_invalid_time_column(self):
        """Test connection with invalid time_column."""
        adapter = SyntheticControlAdapter()

        with pytest.raises(ValueError, match="time_column must be a string"):
            adapter.connect(
                {
                    "unit_column": "unit_id",
                    "time_column": 123,
                    "outcome_column": "revenue",
                }
            )

    def test_connect_missing_outcome_column(self):
        """Test connection with missing outcome_column."""
        adapter = SyntheticControlAdapter()

        with pytest.raises(ValueError, match="outcome_column is required"):
            adapter.connect({"unit_column": "unit_id", "time_column": "date"})


class TestSyntheticControlAdapterValidateConnection:
    """Tests for validate_connection() method."""

    def test_validate_connection_success(self):
        """Test connection validation when connected."""
        adapter = SyntheticControlAdapter()
        adapter.connect(merge_model_params({"outcome_column": "outcome"}))

        assert adapter.validate_connection() is True

    def test_validate_connection_not_connected(self):
        """Test connection validation when not connected."""
        adapter = SyntheticControlAdapter()

        assert adapter.validate_connection() is False


class TestSyntheticControlAdapterValidateParams:
    """Tests for validate_params() method."""

    def test_validate_params_valid(self):
        """Test validation with all required params."""
        adapter = SyntheticControlAdapter()
        params = {
            "treatment_time": "2024-01-21",
            "treated_unit": "treated",
            "outcome_column": "outcome",
        }

        # Should not raise
        adapter.validate_params(params)

    def test_validate_params_missing_treatment_time(self):
        """Test validation with missing treatment_time."""
        adapter = SyntheticControlAdapter()

        with pytest.raises(ValueError, match="treatment_time is required"):
            adapter.validate_params({"treated_unit": "treated", "outcome_column": "outcome"})

    def test_validate_params_missing_treated_unit(self):
        """Test validation with missing treated_unit."""
        adapter = SyntheticControlAdapter()

        with pytest.raises(ValueError, match="treated_unit is required"):
            adapter.validate_params({"treatment_time": "2024-01-21", "outcome_column": "outcome"})

    def test_validate_params_missing_outcome_column(self):
        """Test validation with missing outcome_column."""
        adapter = SyntheticControlAdapter()

        with pytest.raises(ValueError, match="outcome_column is required"):
            adapter.validate_params({"treatment_time": "2024-01-21", "treated_unit": "treated"})


class TestSyntheticControlAdapterGetFitParams:
    """Tests for get_fit_params() method."""

    def test_accepted_params_pass_through(self):
        """Verify only SC-relevant params pass through."""
        adapter = SyntheticControlAdapter()
        params = {
            "treatment_time": "2024-01-21",
            "treated_unit": "treated",
            "unit_column": "unit_id",
            "outcome_column": "outcome",
            "time_column": "date",
            "optim_method": "Nelder-Mead",
            "optim_initial": "equal",
            # Other models' params
            "intervention_date": "2024-01-15",
            "order": [1, 0, 0],
            "formula": "y ~ x",
            "n_strata": 5,
        }

        filtered = adapter.get_fit_params(params)

        assert set(filtered.keys()) == {
            "treatment_time",
            "treated_unit",
            "unit_column",
            "outcome_column",
            "time_column",
            "optim_method",
            "optim_initial",
        }

    def test_irrelevant_params_excluded(self):
        """Verify config keys from other models are excluded."""
        adapter = SyntheticControlAdapter()
        params = {
            "treatment_time": "2024-01-21",
            "intervention_date": "2024-01-15",
            "order": [1, 0, 0],
            "seasonal_order": [0, 0, 0, 0],
            "formula": "y ~ x",
            "n_strata": 5,
        }

        filtered = adapter.get_fit_params(params)

        assert "intervention_date" not in filtered
        assert "order" not in filtered
        assert "seasonal_order" not in filtered
        assert "formula" not in filtered
        assert "n_strata" not in filtered

    def test_empty_params(self):
        """Verify empty params returns empty dict."""
        adapter = SyntheticControlAdapter()

        assert adapter.get_fit_params({}) == {}


class TestSyntheticControlAdapterFit:
    """Tests for fit() method — real e2e through pysyncon."""

    def test_fit_not_connected(self):
        """Test fitting without connection."""
        adapter = SyntheticControlAdapter()
        data = _make_panel_data()

        with pytest.raises(ConnectionError, match="Model not connected"):
            adapter.fit(data, treatment_time="2024-01-21", treated_unit="treated")

    def test_fit_returns_model_result(self):
        """Test that fit returns ModelResult with correct model_type."""
        adapter = SyntheticControlAdapter()
        adapter.connect({"outcome_column": "outcome"})

        data = _make_panel_data()
        treatment_time = pd.Timestamp("2024-01-21")

        result = adapter.fit(
            data,
            treatment_time=treatment_time,
            treated_unit="treated",
            outcome_column="outcome",
        )

        assert isinstance(result, ModelResult)
        assert result.model_type == "synthetic_control"

    def test_fit_result_data_structure(self):
        """Test that fit result has standardized three-key structure."""
        adapter = SyntheticControlAdapter()
        adapter.connect({"outcome_column": "outcome"})

        data = _make_panel_data()
        treatment_time = pd.Timestamp("2024-01-21")

        result = adapter.fit(
            data,
            treatment_time=treatment_time,
            treated_unit="treated",
            outcome_column="outcome",
        )

        assert "model_params" in result.data
        assert "impact_estimates" in result.data
        assert "model_summary" in result.data
        assert result.data["model_params"]["treatment_time"] == str(treatment_time)
        assert result.data["model_params"]["treated_unit"] == "treated"

    def test_fit_impact_estimates_structure(self):
        """Test that impact estimates have all expected fields."""
        adapter = SyntheticControlAdapter()
        adapter.connect({"outcome_column": "outcome"})

        data = _make_panel_data()
        treatment_time = pd.Timestamp("2024-01-21")

        result = adapter.fit(
            data,
            treatment_time=treatment_time,
            treated_unit="treated",
            outcome_column="outcome",
        )

        estimates = result.data["impact_estimates"]
        expected_keys = {
            "att",
            "se",
            "ci_lower",
            "ci_upper",
            "cumulative_effect",
        }
        assert set(estimates.keys()) == expected_keys

        # All values must be numeric
        for key in expected_keys:
            assert isinstance(estimates[key], (int, float)), f"{key} is not numeric"

    def test_fit_model_summary_structure(self):
        """Test that model summary has all expected fields."""
        adapter = SyntheticControlAdapter()
        adapter.connect({"outcome_column": "outcome"})

        data = _make_panel_data(n_pre=20, n_post=10)
        treatment_time = pd.Timestamp("2024-01-21")

        result = adapter.fit(
            data,
            treatment_time=treatment_time,
            treated_unit="treated",
            outcome_column="outcome",
        )

        summary = result.data["model_summary"]
        assert summary["n_pre_periods"] == 20
        assert summary["n_post_periods"] == 10
        assert summary["n_control_units"] == 4
        assert "mspe" in summary
        assert "mae" in summary
        assert "weights" in summary
        assert isinstance(summary["weights"], dict)
        assert result.data["model_params"]["treated_unit"] == "treated"
        assert result.data["model_params"]["treatment_time"] == str(treatment_time)

    def test_fit_detects_positive_effect(self):
        """Test that a clear positive treatment effect is detected."""
        adapter = SyntheticControlAdapter()
        adapter.connect({"outcome_column": "outcome"})

        data = _make_panel_data(treatment_effect=20.0)
        treatment_time = pd.Timestamp("2024-01-21")

        result = adapter.fit(
            data,
            treatment_time=treatment_time,
            treated_unit="treated",
            outcome_column="outcome",
        )

        estimates = result.data["impact_estimates"]
        # With a large effect of 20, ATT should be positive
        assert estimates["att"] > 0


class TestSyntheticControlAdapterValidateData:
    """Tests for validate_data() method."""

    def test_valid_data(self):
        """Test validation with valid panel data."""
        adapter = SyntheticControlAdapter()
        adapter.connect({"outcome_column": "outcome"})

        data = _make_panel_data()
        assert adapter.validate_data(data) is True

    def test_empty_dataframe(self):
        """Test validation with empty DataFrame."""
        adapter = SyntheticControlAdapter()
        adapter.connect({"outcome_column": "outcome"})

        assert adapter.validate_data(pd.DataFrame()) is False

    def test_none_data(self):
        """Test validation with None."""
        adapter = SyntheticControlAdapter()
        adapter.connect({"outcome_column": "outcome"})

        assert adapter.validate_data(None) is False

    def test_missing_columns(self):
        """Test validation with missing required columns."""
        adapter = SyntheticControlAdapter()
        adapter.connect({"outcome_column": "outcome"})

        data = pd.DataFrame({"other_col": [1, 2, 3]})
        assert adapter.validate_data(data) is False


class TestSyntheticControlAdapterGetRequiredColumns:
    """Tests for get_required_columns() method."""

    def test_required_columns_default(self):
        """Test default required columns before connect."""
        adapter = SyntheticControlAdapter()

        columns = adapter.get_required_columns()
        assert "unit_id" in columns
        assert "date" in columns

    def test_required_columns_custom(self):
        """Test required columns after connect with custom names."""
        adapter = SyntheticControlAdapter()
        adapter.connect(
            {
                "unit_column": "region",
                "time_column": "period",
                "outcome_column": "sales",
            }
        )

        columns = adapter.get_required_columns()
        assert "region" in columns
        assert "period" in columns
