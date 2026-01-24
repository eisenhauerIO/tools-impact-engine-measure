"""Tests for transforms module."""

import pandas as pd
import pytest

# Import registry from core
from impact_engine.core import (
    TRANSFORM_REGISTRY,
    apply_transform,
    get_transform,
    register_transform,
)

# Import transforms from their colocated locations (triggers registration)
from impact_engine.models.interrupted_time_series import aggregate_by_date
from impact_engine.models.metrics_approximation import aggregate_for_approximation


class TestTransformRegistry:
    """Tests for transform registry functions."""

    def test_get_transform_aggregate_by_date(self):
        """Test getting aggregate_by_date transform."""
        transform = get_transform("aggregate_by_date")
        assert transform is aggregate_by_date
        assert callable(transform)

    def test_get_transform_aggregate_for_approximation(self):
        """Test getting aggregate_for_approximation transform."""
        transform = get_transform("aggregate_for_approximation")
        assert transform is aggregate_for_approximation
        assert callable(transform)

    def test_get_transform_passthrough(self):
        """Test getting passthrough transform."""
        transform = get_transform("passthrough")
        assert callable(transform)

    def test_get_transform_unknown_raises(self):
        """Test that unknown transform raises ValueError."""
        with pytest.raises(ValueError, match="Unknown transform"):
            get_transform("nonexistent_transform")

    def test_get_transform_error_message_includes_available(self):
        """Test that error message lists available transforms."""
        with pytest.raises(ValueError, match="aggregate_by_date"):
            get_transform("nonexistent")

    def test_register_transform_decorator(self):
        """Test registering a custom transform."""

        @register_transform("test_custom_transform")
        def custom_transform(df: pd.DataFrame, params: dict) -> pd.DataFrame:
            return df

        assert "test_custom_transform" in TRANSFORM_REGISTRY.keys()
        assert get_transform("test_custom_transform") is custom_transform

        # Cleanup
        del TRANSFORM_REGISTRY._registry["test_custom_transform"]

    def test_register_non_callable_raises(self):
        """Test that registering non-callable raises ValueError."""
        decorator = register_transform("bad_transform")
        with pytest.raises(ValueError, match="must be callable"):
            decorator("not a function")


class TestApplyTransform:
    """Tests for apply_transform function."""

    def test_apply_transform_with_config(self):
        """Test applying transform via config dict."""
        data = pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-01", "2024-01-02"],
                "revenue": [100, 200, 150],
            }
        )
        config = {"FUNCTION": "aggregate_by_date", "PARAMS": {"metric": "revenue"}}

        result = apply_transform(data, config)

        assert len(result) == 2
        assert result[result["date"] == "2024-01-01"]["revenue"].iloc[0] == 300

    def test_apply_transform_missing_function_raises(self):
        """Test that missing FUNCTION key raises ValueError."""
        data = pd.DataFrame({"x": [1, 2, 3]})
        config = {"PARAMS": {"metric": "x"}}

        with pytest.raises(ValueError, match="FUNCTION"):
            apply_transform(data, config)

    def test_apply_transform_default_params(self):
        """Test apply_transform with no PARAMS uses defaults."""
        data = pd.DataFrame({"x": [1, 2, 3]})
        config = {"FUNCTION": "passthrough"}

        result = apply_transform(data, config)
        pd.testing.assert_frame_equal(result, data)


class TestAggregateByDate:
    """Tests for aggregate_by_date transform."""

    def test_basic_aggregation(self):
        """Test basic date aggregation."""
        data = pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02"],
                "revenue": [100, 200, 150, 250],
                "units": [10, 20, 15, 25],
            }
        )

        result = aggregate_by_date(data, {"metric": "revenue"})

        assert len(result) == 2
        assert result[result["date"] == "2024-01-01"]["revenue"].iloc[0] == 300
        assert result[result["date"] == "2024-01-02"]["revenue"].iloc[0] == 400
        assert result[result["date"] == "2024-01-01"]["units"].iloc[0] == 30

    def test_default_metric_revenue(self):
        """Test that default metric is revenue."""
        data = pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-01"],
                "revenue": [100, 200],
            }
        )

        result = aggregate_by_date(data, {})

        assert len(result) == 1
        assert result["revenue"].iloc[0] == 300

    def test_missing_date_column_raises(self):
        """Test that missing date column raises ValueError."""
        data = pd.DataFrame({"revenue": [100, 200]})

        with pytest.raises(ValueError, match="date"):
            aggregate_by_date(data, {"metric": "revenue"})

    def test_missing_metric_column_raises(self):
        """Test that missing metric column raises ValueError."""
        data = pd.DataFrame({"date": ["2024-01-01"], "other": [100]})

        with pytest.raises(ValueError, match="revenue"):
            aggregate_by_date(data, {"metric": "revenue"})

    def test_custom_metric(self):
        """Test aggregation with custom metric."""
        data = pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-01"],
                "custom_metric": [100, 200],
            }
        )

        result = aggregate_by_date(data, {"metric": "custom_metric"})

        assert result["custom_metric"].iloc[0] == 300


class TestAggregateForApproximation:
    """Tests for aggregate_for_approximation transform."""

    def test_basic_aggregation_with_product_id(self):
        """Test basic aggregation with product_id column."""
        data = pd.DataFrame(
            {
                "product_id": ["P001", "P001", "P002", "P002"],
                "revenue": [100, 200, 150, 250],
            }
        )

        result = aggregate_for_approximation(data, {"baseline_metric": "revenue"})

        assert len(result) == 2
        assert list(result.columns) == ["product_id", "baseline_sales"]
        assert result[result["product_id"] == "P001"]["baseline_sales"].iloc[0] == 300
        assert result[result["product_id"] == "P002"]["baseline_sales"].iloc[0] == 400

    def test_aggregation_multiple_products(self):
        """Test aggregation with multiple products."""
        data = pd.DataFrame(
            {
                "product_id": ["A001", "A001", "A002"],
                "revenue": [100, 200, 300],
            }
        )

        result = aggregate_for_approximation(data, {"baseline_metric": "revenue"})

        assert list(result.columns) == ["product_id", "baseline_sales"]
        assert result[result["product_id"] == "A001"]["baseline_sales"].iloc[0] == 300
        assert result[result["product_id"] == "A002"]["baseline_sales"].iloc[0] == 300

    def test_default_baseline_metric(self):
        """Test default baseline_metric is revenue."""
        data = pd.DataFrame(
            {
                "product_id": ["P001", "P001"],
                "revenue": [100, 200],
            }
        )

        result = aggregate_for_approximation(data, {})

        assert result["baseline_sales"].iloc[0] == 300

    def test_missing_id_column_raises(self):
        """Test missing product_id raises ValueError."""
        data = pd.DataFrame({"revenue": [100, 200]})

        with pytest.raises(ValueError, match="product_id"):
            aggregate_for_approximation(data, {})

    def test_missing_baseline_metric_raises(self):
        """Test missing baseline metric raises ValueError."""
        data = pd.DataFrame(
            {
                "product_id": ["P001"],
                "other": [100],
            }
        )

        with pytest.raises(ValueError, match="revenue"):
            aggregate_for_approximation(data, {"baseline_metric": "revenue"})


class TestPassthrough:
    """Tests for passthrough transform."""

    def test_passthrough_returns_same_data(self):
        """Test passthrough returns identical data."""
        data = pd.DataFrame({"x": [1, 2, 3], "y": ["a", "b", "c"]})

        result = get_transform("passthrough")(data, {})

        pd.testing.assert_frame_equal(result, data)

    def test_passthrough_ignores_params(self):
        """Test passthrough ignores any params."""
        data = pd.DataFrame({"x": [1]})

        result = get_transform("passthrough")(data, {"unused": "param"})

        pd.testing.assert_frame_equal(result, data)
