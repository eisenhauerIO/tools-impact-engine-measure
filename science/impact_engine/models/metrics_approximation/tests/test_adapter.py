"""Tests for MetricsApproximationAdapter."""

import pandas as pd
import pytest

from impact_engine.models.conftest import merge_model_params
from impact_engine.models.metrics_approximation.adapter import MetricsApproximationAdapter


def create_test_data():
    """Create test data for metrics approximation."""
    return pd.DataFrame(
        {
            "product_id": ["P001", "P002", "P003", "P004", "P005"],
            "quality_before": [0.45, 0.30, 0.55, 0.40, 0.35],
            "quality_after": [0.85, 0.75, 0.90, 0.80, 0.70],
            "baseline_sales": [100.0, 150.0, 200.0, 120.0, 180.0],
        }
    )


class TestMetricsApproximationAdapterConnect:
    """Tests for connect() method."""

    def test_connect_with_defaults(self):
        """Connect with default configuration."""
        adapter = MetricsApproximationAdapter()
        config = merge_model_params({"response": {"FUNCTION": "linear"}})
        result = adapter.connect(config)

        assert result is True
        assert adapter.is_connected is True
        assert adapter.config["metric_before_column"] == "quality_before"
        assert adapter.config["metric_after_column"] == "quality_after"
        assert adapter.config["baseline_column"] == "baseline_sales"
        assert adapter.config["response_function"] == "linear"

    def test_connect_with_custom_columns(self):
        """Connect with custom column names."""
        adapter = MetricsApproximationAdapter()
        config = {
            "metric_before_column": "score_pre",
            "metric_after_column": "score_post",
            "baseline_column": "revenue",
            "response": {"FUNCTION": "linear", "PARAMS": {"coefficient": 0.5}},
        }
        result = adapter.connect(config)

        assert result is True
        assert adapter.config["metric_before_column"] == "score_pre"
        assert adapter.config["metric_after_column"] == "score_post"
        assert adapter.config["baseline_column"] == "revenue"
        assert adapter.config["response_params"]["coefficient"] == 0.5

    def test_connect_invalid_response_function(self):
        """Invalid response function raises ValueError."""
        adapter = MetricsApproximationAdapter()
        config = merge_model_params({"response": {"FUNCTION": "nonexistent"}})

        with pytest.raises(ValueError, match="Invalid response function"):
            adapter.connect(config)

    def test_connect_missing_function_key(self):
        """Missing FUNCTION key raises ValueError."""
        adapter = MetricsApproximationAdapter()
        config = merge_model_params({})
        # Replace response entirely to remove FUNCTION key
        config["response"] = {"PARAMS": {"coefficient": 0.5}}

        with pytest.raises(ValueError, match="FUNCTION is required"):
            adapter.connect(config)

    def test_connect_invalid_response_type(self):
        """Non-dict response raises ValueError."""
        adapter = MetricsApproximationAdapter()
        config = merge_model_params({})
        # Replace response with non-dict to test validation
        config["response"] = "linear"

        with pytest.raises(ValueError, match="must be a dict"):
            adapter.connect(config)


class TestMetricsApproximationAdapterValidateConnection:
    """Tests for validate_connection() method."""

    def test_validate_connected(self):
        """Returns True when connected."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(merge_model_params({"response": {"FUNCTION": "linear"}}))

        assert adapter.validate_connection() is True

    def test_validate_not_connected(self):
        """Returns False when not connected."""
        adapter = MetricsApproximationAdapter()

        assert adapter.validate_connection() is False


class TestMetricsApproximationAdapterFit:
    """Tests for fit() method."""

    def test_fit_basic(self):
        """Basic fit with default configuration."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(
            merge_model_params({"response": {"FUNCTION": "linear", "PARAMS": {"coefficient": 0.5}}})
        )

        data = create_test_data()
        results = adapter.fit(data)

        assert results["model_type"] == "metrics_approximation"
        assert results["response_function"] == "linear"
        assert results["impact_estimates"]["n_products"] == 5
        assert len(results["per_product"]) == 5

    def test_fit_calculates_correct_impact(self):
        """Verify impact calculation is correct."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(
            merge_model_params({"response": {"FUNCTION": "linear", "PARAMS": {"coefficient": 0.5}}})
        )

        # Single product for easy verification
        data = pd.DataFrame(
            {
                "product_id": ["P001"],
                "quality_before": [0.40],
                "quality_after": [0.80],  # delta = 0.4
                "baseline_sales": [100.0],
            }
        )

        results = adapter.fit(data)

        # Expected: 0.4 * 100 * 0.5 = 20.0
        product_result = results["per_product"][0]
        assert product_result["delta_metric"] == 0.4
        assert product_result["approximated_impact"] == 20.0
        assert results["impact_estimates"]["total_approximated_impact"] == 20.0

    def test_fit_aggregate_statistics(self):
        """Verify aggregate statistics are correct."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(
            merge_model_params({"response": {"FUNCTION": "linear", "PARAMS": {"coefficient": 1.0}}})
        )

        data = pd.DataFrame(
            {
                "product_id": ["P001", "P002"],
                "quality_before": [0.4, 0.3],
                "quality_after": [0.8, 0.6],  # deltas: 0.4, 0.3
                "baseline_sales": [100.0, 200.0],  # impacts: 40, 60
            }
        )

        results = adapter.fit(data)

        assert results["impact_estimates"]["total_approximated_impact"] == 100.0
        assert results["impact_estimates"]["mean_approximated_impact"] == 50.0
        assert results["impact_estimates"]["mean_metric_change"] == 0.35
        assert results["impact_estimates"]["n_products"] == 2

    def test_fit_not_connected_raises(self):
        """Fit without connect raises ConnectionError."""
        adapter = MetricsApproximationAdapter()
        data = create_test_data()

        with pytest.raises(ConnectionError, match="not connected"):
            adapter.fit(data)

    def test_fit_missing_columns_raises(self):
        """Missing required columns raises ValueError."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(merge_model_params({"response": {"FUNCTION": "linear"}}))

        data = pd.DataFrame(
            {
                "product_id": ["P001"],
                "quality_before": [0.4],
                # Missing quality_after and baseline_sales
            }
        )

        with pytest.raises(ValueError, match="validation failed"):
            adapter.fit(data)

    def test_fit_empty_data_raises(self):
        """Empty DataFrame raises ValueError."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(merge_model_params({"response": {"FUNCTION": "linear"}}))

        data = pd.DataFrame()

        with pytest.raises(ValueError, match="validation failed"):
            adapter.fit(data)


class TestMetricsApproximationAdapterValidateData:
    """Tests for validate_data() method."""

    def test_valid_data(self):
        """Valid data returns True."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(merge_model_params({"response": {"FUNCTION": "linear"}}))

        data = create_test_data()
        assert adapter.validate_data(data) is True

    def test_empty_dataframe(self):
        """Empty DataFrame returns False."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(merge_model_params({"response": {"FUNCTION": "linear"}}))

        data = pd.DataFrame()
        assert adapter.validate_data(data) is False

    def test_none_data(self):
        """None data returns False."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(merge_model_params({"response": {"FUNCTION": "linear"}}))

        assert adapter.validate_data(None) is False

    def test_missing_columns(self):
        """Missing columns returns False."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(merge_model_params({"response": {"FUNCTION": "linear"}}))

        data = pd.DataFrame(
            {
                "product_id": ["P001"],
                "other_column": [1.0],
            }
        )
        assert adapter.validate_data(data) is False


class TestMetricsApproximationAdapterGetRequiredColumns:
    """Tests for get_required_columns() method."""

    def test_default_columns(self):
        """Returns default columns when not connected."""
        adapter = MetricsApproximationAdapter()
        columns = adapter.get_required_columns()

        assert "quality_before" in columns
        assert "quality_after" in columns
        assert "baseline_sales" in columns

    def test_custom_columns(self):
        """Returns configured columns when connected."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(
            {
                "metric_before_column": "score_pre",
                "metric_after_column": "score_post",
                "baseline_column": "revenue",
                "response": {"FUNCTION": "linear"},
            }
        )

        columns = adapter.get_required_columns()

        assert "score_pre" in columns
        assert "score_post" in columns
        assert "revenue" in columns
