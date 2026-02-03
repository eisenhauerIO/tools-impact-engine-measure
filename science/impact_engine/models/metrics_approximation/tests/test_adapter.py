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
        results = adapter.fit(data, storage=mock_storage)

        assert results.model_type == "metrics_approximation"
        assert results.data["response_function"] == "linear"
        assert results.data["impact_estimates"]["n_products"] == 5

        # Per-product written to parquet, not in result
        call_args = mock_storage.write_parquet.call_args
        assert call_args[0][0] == "product_level_impacts.parquet"
        assert len(call_args[0][1]) == 5

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

        results = adapter.fit(data, storage=mock_storage)

        # Expected: 0.4 * 100 * 0.5 = 20.0
        per_product_df = mock_storage.write_parquet.call_args[0][1]
        assert per_product_df.iloc[0]["delta_metric"] == 0.4
        assert per_product_df.iloc[0]["impact"] == 20.0
        assert results.data["impact_estimates"]["impact"] == 20.0

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

        results = adapter.fit(data, storage=mock_storage)

        assert results.data["impact_estimates"]["impact"] == 100.0
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

        adapter.fit(data, storage=mock_storage)

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

        adapter.fit(data, storage=mock_storage)

        # Electronics: 0.4 * 100 * 0.8 = 32.0
        # Clothing: 0.4 * 100 * 0.5 = 20.0
        per_product_df = mock_storage.write_parquet.call_args[0][1]
        assert per_product_df.iloc[0]["impact"] == 32.0
        assert per_product_df.iloc[1]["impact"] == 20.0


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

        results = adapter.fit(data, storage=mock_storage)

        assert results.data["impact_estimates"]["n_products"] == 2
        # Find the product_level_impacts.parquet call
        per_product_call = [
            c
            for c in mock_storage.write_parquet.call_args_list
            if c[0][0] == "product_level_impacts.parquet"
        ][0]
        product_ids = list(per_product_call[0][1]["product_id"])
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

        results = adapter.fit(data, storage=mock_storage)

        assert results.data["impact_estimates"]["n_products"] == 1
        per_product_call = [
            c
            for c in mock_storage.write_parquet.call_args_list
            if c[0][0] == "product_level_impacts.parquet"
        ][0]
        assert per_product_call[0][1].iloc[0]["product_id"] == "P002"

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

        results = adapter.fit(data, storage=mock_storage)

        assert results.data["impact_estimates"]["n_products"] == 1
        per_product_call = [
            c
            for c in mock_storage.write_parquet.call_args_list
            if c[0][0] == "product_level_impacts.parquet"
        ][0]
        assert per_product_call[0][1].iloc[0]["product_id"] == "P001"

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

        results = adapter.fit(data, storage=mock_storage)

        assert results.data["impact_estimates"]["n_products"] == 0
        assert results.data["impact_estimates"]["impact"] == 0.0
        # No product_level_impacts.parquet written when all rows filtered
        product_level_calls = [
            c
            for c in mock_storage.write_parquet.call_args_list
            if c[0][0] == "product_level_impacts.parquet"
        ]
        assert len(product_level_calls) == 0

    def test_fit_no_missing_values_processes_all(self, mock_storage):
        """Data with no missing values processes all rows."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(
            merge_model_params({"RESPONSE": {"FUNCTION": "linear", "PARAMS": {"coefficient": 1.0}}})
        )

        data = create_test_data()
        results = adapter.fit(data, storage=mock_storage)

        assert results.data["impact_estimates"]["n_products"] == 5

    def test_fit_writes_filtered_products_parquet(self, mock_storage):
        """Filtered products are written to parquet via storage."""
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

        adapter.fit(data, storage=mock_storage)

        # Two parquets written: filtered_products.parquet and product_level_impacts.parquet
        filtered_call = [
            c
            for c in mock_storage.write_parquet.call_args_list
            if c[0][0] == "filtered_products.parquet"
        ][0]
        written_df = filtered_call[0][1]
        assert list(written_df["product_id"]) == ["P002", "P003"]

    def test_fit_no_filtered_parquet_written_when_no_filtered_products(self, mock_storage):
        """No filtered_products.parquet written when all products are valid."""
        adapter = MetricsApproximationAdapter()
        adapter.connect(
            merge_model_params({"RESPONSE": {"FUNCTION": "linear", "PARAMS": {"coefficient": 1.0}}})
        )

        data = create_test_data()  # No NaN values

        adapter.fit(data, storage=mock_storage)

        # Only product_level_impacts.parquet written, not filtered_products.parquet
        filtered_calls = [
            c
            for c in mock_storage.write_parquet.call_args_list
            if c[0][0] == "filtered_products.parquet"
        ]
        assert len(filtered_calls) == 0


class TestMetricsApproximationAdapterMultiOutput:
    """Tests for multi-output response functions."""

    def test_fit_multi_output_response(self, mock_storage):
        """Response function returning dict produces multiple columns."""
        from impact_engine.models.metrics_approximation.response_registry import (
            register_response_function,
        )

        def multi_output_response(delta_metric, baseline_outcome, **kwargs):
            """Return impact with confidence bounds."""
            impact = delta_metric * baseline_outcome
            return {
                "impact": impact,
                "lower": impact * 0.8,
                "upper": impact * 1.2,
            }

        register_response_function("multi_output", multi_output_response)

        adapter = MetricsApproximationAdapter()
        adapter.connect(merge_model_params({"RESPONSE": {"FUNCTION": "multi_output"}}))

        data = pd.DataFrame(
            {
                "product_id": ["P001", "P002"],
                "quality_before": [0.4, 0.3],
                "quality_after": [0.8, 0.6],  # deltas: 0.4, 0.3
                "baseline_sales": [100.0, 200.0],  # impacts: 40, 60
            }
        )

        results = adapter.fit(data, storage=mock_storage)

        # Verify per-product parquet has all columns
        per_product_df = mock_storage.write_parquet.call_args[0][1]
        assert "impact" in per_product_df.columns
        assert "lower" in per_product_df.columns
        assert "upper" in per_product_df.columns

        # P001: impact=40, lower=32, upper=48
        # P002: impact=60, lower=48, upper=72
        assert per_product_df.iloc[0]["impact"] == 40.0
        assert per_product_df.iloc[0]["lower"] == 32.0
        assert per_product_df.iloc[0]["upper"] == 48.0

        # Verify aggregates
        assert results.data["impact_estimates"]["impact"] == 100.0
        assert results.data["impact_estimates"]["lower"] == 80.0
        assert results.data["impact_estimates"]["upper"] == 120.0
        assert results.data["impact_estimates"]["n_products"] == 2

    def test_fit_custom_key_names(self, mock_storage):
        """Response function can use any key names."""
        from impact_engine.models.metrics_approximation.response_registry import (
            register_response_function,
        )

        def custom_keys_response(delta_metric, baseline_outcome, **kwargs):
            """Return with custom key names."""
            value = delta_metric * baseline_outcome
            return {
                "point_estimate": value,
                "ci_low": value * 0.9,
                "ci_high": value * 1.1,
            }

        register_response_function("custom_keys", custom_keys_response)

        adapter = MetricsApproximationAdapter()
        adapter.connect(merge_model_params({"RESPONSE": {"FUNCTION": "custom_keys"}}))

        data = pd.DataFrame(
            {
                "product_id": ["P001"],
                "quality_before": [0.4],
                "quality_after": [0.8],
                "baseline_sales": [100.0],
            }
        )

        results = adapter.fit(data, storage=mock_storage)

        # Verify custom keys are used
        per_product_df = mock_storage.write_parquet.call_args[0][1]
        assert "point_estimate" in per_product_df.columns
        assert "ci_low" in per_product_df.columns
        assert "ci_high" in per_product_df.columns

        assert results.data["impact_estimates"]["point_estimate"] == 40.0
        assert results.data["impact_estimates"]["ci_low"] == 36.0
        assert results.data["impact_estimates"]["ci_high"] == 44.0
