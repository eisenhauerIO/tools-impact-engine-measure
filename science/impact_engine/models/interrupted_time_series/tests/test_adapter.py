"""Tests for InterruptedTimeSeriesAdapter."""

import tempfile

import pandas as pd
import pytest
from artifact_store import ArtifactStore

from impact_engine.models.interrupted_time_series import InterruptedTimeSeriesAdapter
from impact_engine.models.interrupted_time_series.adapter import TransformedInput


class TestInterruptedTimeSeriesAdapter:
    """Tests for InterruptedTimeSeriesAdapter functionality."""

    def _setup_model_with_storage(self, tmpdir):
        """Helper method to set up model with storage backend."""
        model = InterruptedTimeSeriesAdapter()
        config = {
            "order": (1, 0, 0),
            "seasonal_order": (0, 0, 0, 0),
            "dependent_variable": "revenue",
        }
        model.connect(config)

        # Set up artifact store
        storage = ArtifactStore(tmpdir)
        model.storage = storage

        return model

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

        with pytest.raises(ValueError, match="Seasonal order must be a tuple of 4 integers"):
            model.connect({"seasonal_order": (1, 2)})

    def test_validate_connection_success(self):
        """Test connection validation when connected."""
        model = InterruptedTimeSeriesAdapter()
        model.connect({"order": (1, 0, 0)})

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
        model.connect({"dependent_variable": "missing_column"})

        data = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10), "revenue": range(10)})

        with pytest.raises(ValueError, match="Dependent variable 'missing_column' not found"):
            model.transform_outbound(data, "2024-01-05")

    def test_transform_inbound_raises_not_implemented(self):
        """Test that transform_inbound raises NotImplementedError (use _format_results instead)."""
        model = InterruptedTimeSeriesAdapter()
        model.connect({"dependent_variable": "revenue"})

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
        model.connect({"dependent_variable": "revenue"})

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

        assert result["model_type"] == "interrupted_time_series"
        assert result["intervention_date"] == "2024-01-05"
        assert result["dependent_variable"] == "revenue"
        assert "impact_estimates" in result
        assert "model_summary" in result

    def test_fit_not_connected(self):
        """Test fitting without connection."""
        model = InterruptedTimeSeriesAdapter()

        data = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10), "revenue": range(10)})

        with pytest.raises(ConnectionError, match="Model not connected"):
            model.fit(data, intervention_date="2024-01-05", output_path="/tmp")

    def test_fit_no_storage(self):
        """Test fitting without storage backend."""
        model = InterruptedTimeSeriesAdapter()

        # Connect the model but don't set storage
        config = {
            "order": (1, 0, 0),
            "seasonal_order": (0, 0, 0, 0),
            "dependent_variable": "revenue",
        }
        model.connect(config)

        data = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10), "revenue": range(10)})

        with pytest.raises(RuntimeError, match="Storage backend is required"):
            model.fit(data, intervention_date="2024-01-05", output_path="results")

    def test_fit_result_file_creation(self):
        """Test that ITS model creates result file at specified path."""
        # Create sample time series data
        data = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=30),
                "revenue": [1000 + i * 10 for i in range(30)],
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            model = self._setup_model_with_storage(tmpdir)

            result_path = model.fit(
                data=data,
                intervention_date="2024-01-15",
                output_path="results",
                dependent_variable="revenue",
            )

            # Verify result path format
            assert result_path.endswith(".json")

    def test_fit_result_file_content(self):
        """Test that ITS model saves valid JSON with required fields."""
        data = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=30),
                "revenue": [1000 + i * 10 for i in range(30)],
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            model = self._setup_model_with_storage(tmpdir)

            model.fit(
                data=data,
                intervention_date="2024-01-15",
                output_path="results",
                dependent_variable="revenue",
            )

            # Load and verify JSON content from storage
            result_data = model.storage.read_json("results/impact_results.json")

            # Verify required fields
            assert result_data["model_type"] == "interrupted_time_series"
            assert result_data["intervention_date"] == "2024-01-15"
            assert result_data["dependent_variable"] == "revenue"
            assert "impact_estimates" in result_data
            assert "model_summary" in result_data

    def test_fit_impact_estimates_structure(self):
        """Test that impact estimates have correct structure."""
        data = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=30),
                "revenue": [1000 + i * 10 for i in range(30)],
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            model = self._setup_model_with_storage(tmpdir)

            model.fit(
                data=data,
                intervention_date="2024-01-15",
                output_path="results",
                dependent_variable="revenue",
            )

            result_data = model.storage.read_json("results/impact_results.json")

            impact_estimates = result_data["impact_estimates"]

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

        with tempfile.TemporaryDirectory() as tmpdir:
            model = self._setup_model_with_storage(tmpdir)

            model.fit(
                data=data,
                intervention_date="2024-01-15",
                output_path="results",
                dependent_variable="revenue",
            )

            result_data = model.storage.read_json("results/impact_results.json")

            model_summary = result_data["model_summary"]

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

    def test_fit_returns_file_path(self):
        """Test that fit method returns the correct storage URL."""
        data = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=30),
                "revenue": [1000 + i * 10 for i in range(30)],
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            model = self._setup_model_with_storage(tmpdir)

            result_path = model.fit(
                data=data,
                intervention_date="2024-01-15",
                output_path="results",
                dependent_variable="revenue",
            )

            # Verify path is a string
            assert isinstance(result_path, str)

            # Verify it's a proper path
            assert "results/impact_results.json" in result_path

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
