"""Tests for InterruptedTimeSeriesAdapter."""

import pandas as pd
import pytest

from impact_engine_measure.models.conftest import merge_model_params
from impact_engine_measure.models.interrupted_time_series import InterruptedTimeSeriesAdapter
from impact_engine_measure.models.interrupted_time_series.adapter import TransformedInput


class TestInterruptedTimeSeriesAdapter:
    """Tests for InterruptedTimeSeriesAdapter functionality."""

    def test_connect_success(self):
        """Test successful model connection."""
        model = InterruptedTimeSeriesAdapter()

        config = {
            "order": (1, 0, 0),
            "seasonal_order": (0, 0, 0, 0),
            "dependent_variable": "revenue",
        }

        result = model.connect(config)
        assert result is True
        assert model.is_connected is True
        assert model.config == config

    def test_connect_invalid_order(self):
        """Test connection with invalid order parameter."""
        model = InterruptedTimeSeriesAdapter()

        with pytest.raises(ValueError, match="Order must be a tuple of 3 integers"):
            model.connect({"order": "invalid"})

    def test_connect_invalid_seasonal_order(self):
        """Test connection with invalid seasonal_order parameter."""
        model = InterruptedTimeSeriesAdapter()
        config = merge_model_params({"seasonal_order": (1, 2)})

        with pytest.raises(ValueError, match="Seasonal order must be a tuple of 4 integers"):
            model.connect(config)

    def test_validate_connection_success(self):
        """Test connection validation when connected."""
        model = InterruptedTimeSeriesAdapter()
        model.connect(merge_model_params({"order": (1, 0, 0)}))

        assert model.validate_connection() is True

    def test_validate_connection_not_connected(self):
        """Test connection validation when not connected."""
        model = InterruptedTimeSeriesAdapter()

        assert model.validate_connection() is False

    def test_transform_outbound_success(self):
        """Test successful outbound transformation."""
        model = InterruptedTimeSeriesAdapter()
        config = {
            "order": (1, 0, 0),
            "seasonal_order": (0, 0, 0, 0),
            "dependent_variable": "revenue",
        }
        model.connect(config)

        data = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10), "revenue": range(10)})

        result = model.transform_outbound(data, "2024-01-05")

        assert "y" in result
        assert "exog" in result
        assert "order" in result
        assert "seasonal_order" in result
        assert result["order"] == (1, 0, 0)
        assert len(result["y"]) == 10
        assert result["exog"].shape == (10, 1)

    def test_transform_outbound_missing_dependent_variable(self):
        """Test outbound transformation with missing dependent variable."""
        model = InterruptedTimeSeriesAdapter()
        model.connect(merge_model_params({"dependent_variable": "missing_column"}))

        data = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10), "revenue": range(10)})

        with pytest.raises(ValueError, match="Dependent variable 'missing_column' not found"):
            model.transform_outbound(data, "2024-01-05")

    def test_transform_inbound_raises_not_implemented(self):
        """Test that transform_inbound raises NotImplementedError (use _format_results instead)."""
        model = InterruptedTimeSeriesAdapter()
        model.connect(merge_model_params({"dependent_variable": "revenue"}))

        # Mock SARIMAX results
        class MockResults:
            def __init__(self):
                self.aic = 100.0
                self.bic = 110.0
                self.params = {"intervention": 5.0}

        with pytest.raises(NotImplementedError, match="transform_inbound requires prior state"):
            model.transform_inbound(MockResults())

    def test_format_results_success(self):
        """Test successful result formatting using stateless _format_results."""
        import numpy as np

        model = InterruptedTimeSeriesAdapter()
        model.connect(merge_model_params({"dependent_variable": "revenue"}))

        # Create TransformedInput with all required data
        data = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=10),
                "revenue": range(10),
                "intervention": [0, 0, 0, 0, 1, 1, 1, 1, 1, 1],
            }
        )

        transformed = TransformedInput(
            y=np.array(range(10)),
            exog=data[["intervention"]],
            data=data,
            dependent_variable="revenue",
            intervention_date="2024-01-05",
            order=(1, 0, 0),
            seasonal_order=(0, 0, 0, 0),
        )

        # Mock SARIMAX results
        class MockResults:
            def __init__(self):
                self.aic = 100.0
                self.bic = 110.0
                self.params = {"intervention": 5.0}

        result = model._format_results(MockResults(), transformed)

        # _format_results returns raw dict; model_type is in ModelResult wrapper
        assert result["model_params"]["intervention_date"] == "2024-01-05"
        assert result["model_params"]["dependent_variable"] == "revenue"
        assert "impact_estimates" in result
        assert "model_summary" in result

    def test_fit_not_connected(self):
        """Test fitting without connection."""
        model = InterruptedTimeSeriesAdapter()

        data = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10), "revenue": range(10)})

        with pytest.raises(ConnectionError, match="Model not connected"):
            model.fit(data, intervention_date="2024-01-05")

    def test_fit_returns_model_result(self):
        """Test that fit returns ModelResult (adapter is storage-agnostic)."""
        from impact_engine_measure.models.base import ModelResult

        model = InterruptedTimeSeriesAdapter()

        config = {
            "order": (1, 0, 0),
            "seasonal_order": (0, 0, 0, 0),
            "dependent_variable": "revenue",
        }
        model.connect(config)

        data = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=30),
                "revenue": [1000 + i * 10 for i in range(30)],
            }
        )

        result = model.fit(data, intervention_date="2024-01-15")

        assert isinstance(result, ModelResult)
        assert result.model_type == "interrupted_time_series"
        assert "impact_estimates" in result.data
        assert "model_summary" in result.data

    def test_fit_result_has_model_type(self):
        """Test that fit returns ModelResult with correct model_type."""
        from impact_engine_measure.models.base import ModelResult

        data = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=30),
                "revenue": [1000 + i * 10 for i in range(30)],
            }
        )

        model = InterruptedTimeSeriesAdapter()
        model.connect(
            {
                "order": (1, 0, 0),
                "seasonal_order": (0, 0, 0, 0),
                "dependent_variable": "revenue",
            }
        )

        result = model.fit(data=data, intervention_date="2024-01-15")

        assert isinstance(result, ModelResult)
        assert result.model_type == "interrupted_time_series"

    def test_fit_result_to_dict_content(self):
        """Test that ModelResult.to_dict() has required fields."""
        data = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=30),
                "revenue": [1000 + i * 10 for i in range(30)],
            }
        )

        model = InterruptedTimeSeriesAdapter()
        model.connect(
            {
                "order": (1, 0, 0),
                "seasonal_order": (0, 0, 0, 0),
                "dependent_variable": "revenue",
            }
        )

        result = model.fit(data=data, intervention_date="2024-01-15")
        result_data = result.to_dict()

        assert result_data["model_type"] == "interrupted_time_series"
        assert result_data["data"]["model_params"]["intervention_date"] == "2024-01-15"
        assert result_data["data"]["model_params"]["dependent_variable"] == "revenue"
        assert "impact_estimates" in result_data["data"]
        assert "model_summary" in result_data["data"]

    def test_fit_impact_estimates_structure(self):
        """Test that impact estimates have correct structure."""
        data = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=30),
                "revenue": [1000 + i * 10 for i in range(30)],
            }
        )

        model = InterruptedTimeSeriesAdapter()
        model.connect(
            {
                "order": (1, 0, 0),
                "seasonal_order": (0, 0, 0, 0),
                "dependent_variable": "revenue",
            }
        )

        result = model.fit(data=data, intervention_date="2024-01-15")
        impact_estimates = result.data["impact_estimates"]

        # Verify impact estimate fields
        assert "intervention_effect" in impact_estimates
        assert "pre_intervention_mean" in impact_estimates
        assert "post_intervention_mean" in impact_estimates
        assert "absolute_change" in impact_estimates
        assert "percent_change" in impact_estimates

        # Verify they are numeric
        assert isinstance(impact_estimates["intervention_effect"], (int, float))
        assert isinstance(impact_estimates["pre_intervention_mean"], (int, float))
        assert isinstance(impact_estimates["post_intervention_mean"], (int, float))

    def test_fit_model_summary_structure(self):
        """Test that model summary has correct structure."""
        data = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=30),
                "revenue": [1000 + i * 10 for i in range(30)],
            }
        )

        model = InterruptedTimeSeriesAdapter()
        model.connect(
            {
                "order": (1, 0, 0),
                "seasonal_order": (0, 0, 0, 0),
                "dependent_variable": "revenue",
            }
        )

        result = model.fit(data=data, intervention_date="2024-01-15")
        model_summary = result.data["model_summary"]

        # Verify model summary fields
        assert "n_observations" in model_summary
        assert "pre_period_length" in model_summary
        assert "post_period_length" in model_summary
        assert "aic" in model_summary
        assert "bic" in model_summary

        # Verify counts are correct
        assert model_summary["n_observations"] == 30
        assert model_summary["pre_period_length"] == 14  # 2024-01-01 to 2024-01-14
        assert model_summary["post_period_length"] == 16  # 2024-01-15 to 2024-01-30

    def test_fit_result_data_structure(self):
        """Test that fit returns ModelResult with correct data structure."""
        from impact_engine_measure.models.base import ModelResult

        data = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=30),
                "revenue": [1000 + i * 10 for i in range(30)],
            }
        )

        model = InterruptedTimeSeriesAdapter()
        model.connect(
            {
                "order": (1, 0, 0),
                "seasonal_order": (0, 0, 0, 0),
                "dependent_variable": "revenue",
            }
        )

        result = model.fit(data=data, intervention_date="2024-01-15")

        # Verify result is ModelResult with standardized three-key structure
        assert isinstance(result, ModelResult)
        assert "model_params" in result.data
        assert "impact_estimates" in result.data
        assert "model_summary" in result.data
        assert result.data["model_params"]["intervention_date"] == "2024-01-15"
        assert result.data["model_params"]["dependent_variable"] == "revenue"

    def test_validate_data_success(self):
        """Test successful data validation."""
        model = InterruptedTimeSeriesAdapter()

        data = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10), "revenue": range(10)})

        assert model.validate_data(data) is True

    def test_validate_data_empty(self):
        """Test data validation with empty DataFrame."""
        model = InterruptedTimeSeriesAdapter()

        data = pd.DataFrame()

        assert model.validate_data(data) is False

    def test_validate_data_missing_date(self):
        """Test data validation with missing date column."""
        model = InterruptedTimeSeriesAdapter()

        data = pd.DataFrame({"revenue": range(10)})

        assert model.validate_data(data) is False

    def test_get_required_columns(self):
        """Test getting required columns."""
        model = InterruptedTimeSeriesAdapter()

        columns = model.get_required_columns()

        assert isinstance(columns, list)
        assert "date" in columns


class TestInterruptedTimeSeriesGetFitParams:
    """Tests for get_fit_params() method."""

    def test_accepted_params_pass_through(self):
        """Verify only ITS-relevant params pass through."""
        model = InterruptedTimeSeriesAdapter()
        params = {
            "intervention_date": "2024-01-15",
            "dependent_variable": "revenue",
            "order": (1, 0, 0),
            "seasonal_order": (0, 0, 0, 0),
            "n_strata": 5,
            "treatment_column": "treated",
            "formula": "y ~ x",
        }

        filtered = model.get_fit_params(params)

        assert set(filtered.keys()) == {
            "intervention_date",
            "dependent_variable",
            "order",
            "seasonal_order",
        }

    def test_irrelevant_params_excluded(self):
        """Verify config keys from other models are excluded."""
        model = InterruptedTimeSeriesAdapter()
        params = {
            "intervention_date": "2024-01-15",
            "n_strata": 5,
            "treatment_column": "treated",
            "covariate_columns": ["x1"],
            "formula": "y ~ x",
        }

        filtered = model.get_fit_params(params)

        assert "n_strata" not in filtered
        assert "treatment_column" not in filtered
        assert "covariate_columns" not in filtered
        assert "formula" not in filtered

    def test_empty_params(self):
        """Verify empty params returns empty dict."""
        model = InterruptedTimeSeriesAdapter()

        assert model.get_fit_params({}) == {}
