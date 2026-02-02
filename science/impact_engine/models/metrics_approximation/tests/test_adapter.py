"""Tests for MetricsApproximationAdapter."""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from impact_engine.models.conftest import merge_model_params
from impact_engine.models.metrics_approximation.adapter import MetricsApproximationAdapter


@pytest.fixture
def mock_storage():
    """Create mock storage for tests."""
    return MagicMock()


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
        config = merge_model_params({"RESPONSE": {"FUNCTION": "linear"}})
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
            "RESPONSE": {"FUNCTION": "linear", "PARAMS": {"coefficient": 0.5}},
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
        config = merge_model_params({"RESPONSE": {"FUNCTION": "nonexistent"}})

        with pytest.raises(ValueError, match="Invalid response function"):
            adapter.connect(config)

    def test_connect_missing_function_key(self):
        """Missing FUNCTION key raises ValueError."""
        adapter = MetricsApproximationAdapter()
        config = merge_model_params({})
        # Replace RESPONSE entirely to remove FUNCTION key
        config["RESPONSE"] = {"PARAMS": {"coefficient": 0.5}}

        with pytest.raises(ValueError, match="FUNCTION is required"):
            adapter.connect(config)

    def test_connect_invalid_response_type(self):
        """Non-dict response raises ValueError."""
        adapter = MetricsApproximationAdapter()
        config = merge_model_params({})
        # Replace RESPONSE with non-dict to test validation
        config["RESPONSE"] = "linear"

        with pytest.raises(ValueError, match="must be a dict"):
            adapter.connect(config)


class TestMetricsApproximationAdapterValidateConnection:
    """Tests for validate_connection() method."""

    def test_validate_connected(self):
        """Returns True when connected."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(merge_model_params({"RESPONSE": {"FUNCTION": "linear"}}))

        assert adapter.validate_connection() is True

    def test_validate_not_connected(self):
        """Returns False when not connected."""
        adapter = MetricsApproximationAdapter()

        assert adapter.validate_connection() is False


class TestMetricsApproximationAdapterFit:
    """Tests for fit() method."""

    def test_fit_basic(self, mock_storage):
        """Basic fit with default configuration."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(
            merge_model_params({"RESPONSE": {"FUNCTION": "linear", "PARAMS": {"coefficient": 0.5}}})
        )

        data = create_test_data()
        results = adapter.fit(data, storage=mock_storage, output_path="results")

        assert results.model_type == "metrics_approximation"
        assert results.data["response_function"] == "linear"
        assert results.data["impact_estimates"]["n_products"] == 5
        assert len(results.data["per_product"]) == 5

    def test_fit_calculates_correct_impact(self, mock_storage):
        """Verify impact calculation is correct."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(
            merge_model_params({"RESPONSE": {"FUNCTION": "linear", "PARAMS": {"coefficient": 0.5}}})
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

        results = adapter.fit(data, storage=mock_storage, output_path="results")

        # Expected: 0.4 * 100 * 0.5 = 20.0
        product_result = results.data["per_product"][0]
        assert product_result["delta_metric"] == 0.4
        assert product_result["approximated_impact"] == 20.0
        assert results.data["impact_estimates"]["total_approximated_impact"] == 20.0

    def test_fit_aggregate_statistics(self, mock_storage):
        """Verify aggregate statistics are correct."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(
            merge_model_params({"RESPONSE": {"FUNCTION": "linear", "PARAMS": {"coefficient": 1.0}}})
        )

        data = pd.DataFrame(
            {
                "product_id": ["P001", "P002"],
                "quality_before": [0.4, 0.3],
                "quality_after": [0.8, 0.6],  # deltas: 0.4, 0.3
                "baseline_sales": [100.0, 200.0],  # impacts: 40, 60
            }
        )

        results = adapter.fit(data, storage=mock_storage, output_path="results")

        assert results.data["impact_estimates"]["total_approximated_impact"] == 100.0
        assert results.data["impact_estimates"]["mean_approximated_impact"] == 50.0
        assert results.data["impact_estimates"]["mean_metric_change"] == 0.35
        assert results.data["impact_estimates"]["n_products"] == 2

    def test_fit_not_connected_raises(self):
        """Fit without connect raises ConnectionError."""
        adapter = MetricsApproximationAdapter()
        data = create_test_data()

        with pytest.raises(ConnectionError, match="not connected"):
            adapter.fit(data)

    def test_fit_missing_columns_raises(self):
        """Missing required columns raises ValueError."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(merge_model_params({"RESPONSE": {"FUNCTION": "linear"}}))

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
        adapter.connect(merge_model_params({"RESPONSE": {"FUNCTION": "linear"}}))

        data = pd.DataFrame()

        with pytest.raises(ValueError, match="validation failed"):
            adapter.fit(data)


class TestMetricsApproximationAdapterValidateData:
    """Tests for validate_data() method."""

    def test_valid_data(self):
        """Valid data returns True."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(merge_model_params({"RESPONSE": {"FUNCTION": "linear"}}))

        data = create_test_data()
        assert adapter.validate_data(data) is True

    def test_empty_dataframe(self):
        """Empty DataFrame returns False."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(merge_model_params({"RESPONSE": {"FUNCTION": "linear"}}))

        data = pd.DataFrame()
        assert adapter.validate_data(data) is False

    def test_none_data(self):
        """None data returns False."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(merge_model_params({"RESPONSE": {"FUNCTION": "linear"}}))

        assert adapter.validate_data(None) is False

    def test_missing_columns(self):
        """Missing columns returns False."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(merge_model_params({"RESPONSE": {"FUNCTION": "linear"}}))

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
                "RESPONSE": {"FUNCTION": "linear"},
            }
        )

        columns = adapter.get_required_columns()

        assert "score_pre" in columns
        assert "score_post" in columns
        assert "revenue" in columns


class TestMetricsApproximationAdapterRowAttributes:
    """Tests for row_attributes passing to response functions."""

    def test_row_attributes_passed_to_response_function(self, mock_storage):
        """Verify row_attributes dict is passed to response function."""
        from impact_engine.models.metrics_approximation.response_registry import (
            register_response_function,
        )

        # Track what was passed to the response function
        captured_attributes = []

        def capture_response(delta_metric, baseline_outcome, **kwargs):
            row_attrs = kwargs.get("row_attributes", {})
            captured_attributes.append(row_attrs)
            return delta_metric * baseline_outcome * 0.5

        register_response_function("capture_test", capture_response)

        adapter = MetricsApproximationAdapter()
        adapter.connect(merge_model_params({"RESPONSE": {"FUNCTION": "capture_test"}}))

        data = pd.DataFrame(
            {
                "product_id": ["P001", "P002"],
                "quality_before": [0.4, 0.3],
                "quality_after": [0.8, 0.6],
                "baseline_sales": [100.0, 200.0],
                "category": ["Electronics", "Clothing"],
                "brand": ["Sony", "Nike"],
            }
        )

        adapter.fit(data, storage=mock_storage, output_path="results")

        # Verify attributes were captured
        assert len(captured_attributes) == 2
        assert captured_attributes[0]["category"] == "Electronics"
        assert captured_attributes[0]["brand"] == "Sony"
        assert captured_attributes[1]["category"] == "Clothing"
        assert captured_attributes[1]["brand"] == "Nike"

    def test_attribute_based_conditioning(self, mock_storage):
        """Verify response function can use attributes for conditional logic."""
        from impact_engine.models.metrics_approximation.response_registry import (
            register_response_function,
        )

        def category_response(delta_metric, baseline_outcome, **kwargs):
            """Apply different coefficients based on category."""
            row_attrs = kwargs.get("row_attributes", {})
            category = row_attrs.get("category")

            if category == "Electronics":
                coefficient = 0.8
            elif category == "Clothing":
                coefficient = 0.5
            else:
                coefficient = 0.3

            return coefficient * delta_metric * baseline_outcome

        register_response_function("category_conditional", category_response)

        adapter = MetricsApproximationAdapter()
        adapter.connect(merge_model_params({"RESPONSE": {"FUNCTION": "category_conditional"}}))

        data = pd.DataFrame(
            {
                "product_id": ["P001", "P002"],
                "quality_before": [0.4, 0.4],
                "quality_after": [0.8, 0.8],  # delta = 0.4 for both
                "baseline_sales": [100.0, 100.0],  # same baseline
                "category": ["Electronics", "Clothing"],
            }
        )

        results = adapter.fit(data, storage=mock_storage, output_path="results")

        # Electronics: 0.4 * 100 * 0.8 = 32.0
        # Clothing: 0.4 * 100 * 0.5 = 20.0
        per_product = results.data["per_product"]
        assert per_product[0]["approximated_impact"] == 32.0
        assert per_product[1]["approximated_impact"] == 20.0


class TestMetricsApproximationAdapterMissingData:
    """Tests for missing data handling in fit() method."""

    def test_fit_filters_rows_with_nan_metric_before(self, mock_storage):
        """Rows with NaN in metric_before are filtered."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(
            merge_model_params({"RESPONSE": {"FUNCTION": "linear", "PARAMS": {"coefficient": 1.0}}})
        )

        data = pd.DataFrame(
            {
                "product_id": ["P001", "P002", "P003"],
                "quality_before": [0.4, float("nan"), 0.3],
                "quality_after": [0.8, 0.6, 0.7],
                "baseline_sales": [100.0, 200.0, 150.0],
            }
        )

        results = adapter.fit(data, storage=mock_storage, output_path="results")

        assert results.data["impact_estimates"]["n_products"] == 2
        product_ids = [p["product_id"] for p in results.data["per_product"]]
        assert "P002" not in product_ids

    def test_fit_filters_rows_with_nan_metric_after(self, mock_storage):
        """Rows with NaN in metric_after are filtered."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(
            merge_model_params({"RESPONSE": {"FUNCTION": "linear", "PARAMS": {"coefficient": 1.0}}})
        )

        data = pd.DataFrame(
            {
                "product_id": ["P001", "P002"],
                "quality_before": [0.4, 0.3],
                "quality_after": [float("nan"), 0.7],
                "baseline_sales": [100.0, 150.0],
            }
        )

        results = adapter.fit(data, storage=mock_storage, output_path="results")

        assert results.data["impact_estimates"]["n_products"] == 1
        assert results.data["per_product"][0]["product_id"] == "P002"

    def test_fit_filters_rows_with_nan_baseline(self, mock_storage):
        """Rows with NaN in baseline are filtered."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(
            merge_model_params({"RESPONSE": {"FUNCTION": "linear", "PARAMS": {"coefficient": 1.0}}})
        )

        data = pd.DataFrame(
            {
                "product_id": ["P001", "P002"],
                "quality_before": [0.4, 0.3],
                "quality_after": [0.8, 0.7],
                "baseline_sales": [100.0, float("nan")],
            }
        )

        results = adapter.fit(data, storage=mock_storage, output_path="results")

        assert results.data["impact_estimates"]["n_products"] == 1
        assert results.data["per_product"][0]["product_id"] == "P001"

    def test_fit_all_rows_filtered_returns_zero_impact(self, mock_storage):
        """All rows filtered returns zero impact (no error)."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(
            merge_model_params({"RESPONSE": {"FUNCTION": "linear", "PARAMS": {"coefficient": 1.0}}})
        )

        data = pd.DataFrame(
            {
                "product_id": ["P001", "P002"],
                "quality_before": [float("nan"), float("nan")],
                "quality_after": [0.8, 0.7],
                "baseline_sales": [100.0, 150.0],
            }
        )

        results = adapter.fit(data, storage=mock_storage, output_path="results")

        assert results.data["impact_estimates"]["n_products"] == 0
        assert results.data["impact_estimates"]["total_approximated_impact"] == 0.0
        assert results.data["impact_estimates"]["mean_approximated_impact"] == 0.0
        assert results.data["per_product"] == []

    def test_fit_no_missing_values_processes_all(self, mock_storage):
        """Data with no missing values processes all rows."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(
            merge_model_params({"RESPONSE": {"FUNCTION": "linear", "PARAMS": {"coefficient": 1.0}}})
        )

        data = create_test_data()
        results = adapter.fit(data, storage=mock_storage, output_path="results")

        assert results.data["impact_estimates"]["n_products"] == 5

    def test_fit_writes_filtered_products_csv(self, mock_storage):
        """Filtered products are written to CSV via storage."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(
            merge_model_params({"RESPONSE": {"FUNCTION": "linear", "PARAMS": {"coefficient": 1.0}}})
        )

        data = pd.DataFrame(
            {
                "product_id": ["P001", "P002", "P003"],
                "quality_before": [0.4, float("nan"), float("nan")],
                "quality_after": [0.8, 0.6, 0.7],
                "baseline_sales": [100.0, 200.0, 150.0],
            }
        )

        adapter.fit(data, storage=mock_storage, output_path="results")

        mock_storage.write_csv.assert_called_once()
        call_args = mock_storage.write_csv.call_args
        assert call_args[0][0] == "results/filtered_products.csv"
        written_df = call_args[0][1]
        assert list(written_df["product_id"]) == ["P002", "P003"]

    def test_fit_no_csv_written_when_no_filtered_products(self, mock_storage):
        """No CSV written when all products are valid."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(
            merge_model_params({"RESPONSE": {"FUNCTION": "linear", "PARAMS": {"coefficient": 1.0}}})
        )

        data = create_test_data()  # No NaN values

        adapter.fit(data, storage=mock_storage, output_path="results")

        mock_storage.write_csv.assert_not_called()
