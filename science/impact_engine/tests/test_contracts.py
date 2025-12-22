"""Tests for data contracts module."""

import pandas as pd
import pytest

from impact_engine.core import MetricsSchema, ProductSchema, Schema


class TestSchema:
    """Tests for the Schema base class."""

    def test_validate_success(self):
        """Validate succeeds when required columns present."""
        schema = Schema(required=["a", "b"], optional=["c"])
        df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
        assert schema.validate(df) is True

    def test_validate_missing_required(self):
        """Validate raises error when required column missing."""
        schema = Schema(required=["a", "b"], optional=["c"])
        df = pd.DataFrame({"a": [1], "c": [3]})
        with pytest.raises(ValueError, match="Missing required columns"):
            schema.validate(df)

    def test_validate_optional_not_required(self):
        """Validate succeeds when optional columns missing."""
        schema = Schema(required=["a"], optional=["b", "c"])
        df = pd.DataFrame({"a": [1]})
        assert schema.validate(df) is True

    def test_from_external_with_mapping(self):
        """from_external renames columns using mapping."""
        schema = Schema(
            required=["product_id"],
            mappings={"source_a": {"external_id": "product_id"}},
        )
        df = pd.DataFrame({"external_id": [1, 2, 3]})
        result = schema.from_external(df, "source_a")
        assert "product_id" in result.columns
        assert "external_id" not in result.columns

    def test_from_external_unknown_source(self):
        """from_external returns copy when source not in mappings."""
        schema = Schema(required=["a"], mappings={"source_a": {"x": "a"}})
        df = pd.DataFrame({"x": [1]})
        result = schema.from_external(df, "unknown_source")
        assert "x" in result.columns
        assert result is not df  # Should be a copy

    def test_to_external_with_mapping(self):
        """to_external renames columns using inverted mapping."""
        schema = Schema(
            required=["product_id"],
            mappings={"target_a": {"external_id": "product_id"}},
        )
        df = pd.DataFrame({"product_id": [1, 2, 3]})
        result = schema.to_external(df, "target_a")
        assert "external_id" in result.columns
        assert "product_id" not in result.columns

    def test_to_external_unknown_target(self):
        """to_external returns copy when target not in mappings."""
        schema = Schema(required=["a"], mappings={"target_a": {"x": "a"}})
        df = pd.DataFrame({"a": [1]})
        result = schema.to_external(df, "unknown_target")
        assert "a" in result.columns

    def test_all_columns(self):
        """all_columns returns required + optional."""
        schema = Schema(required=["a", "b"], optional=["c", "d"])
        assert schema.all_columns() == ["a", "b", "c", "d"]

    def test_roundtrip_transformation(self):
        """from_external and to_external are inverses."""
        schema = Schema(
            required=["product_id", "value"],
            mappings={"external": {"ext_id": "product_id", "ext_val": "value"}},
        )
        original = pd.DataFrame({"ext_id": [1, 2], "ext_val": [10, 20]})
        standardized = schema.from_external(original, "external")
        back = schema.to_external(standardized, "external")
        assert list(back.columns) == list(original.columns)
        assert back["ext_id"].tolist() == original["ext_id"].tolist()


class TestProductSchema:
    """Tests for the ProductSchema instance."""

    def test_required_columns(self):
        """ProductSchema requires product_id."""
        assert ProductSchema.required == ["product_id"]

    def test_optional_columns(self):
        """ProductSchema has name, category, price as optional."""
        assert "name" in ProductSchema.optional
        assert "category" in ProductSchema.optional
        assert "price" in ProductSchema.optional

    def test_catalog_simulator_mapping(self):
        """ProductSchema maps asin to product_id for catalog_simulator."""
        df = pd.DataFrame({"asin": ["A001", "A002"]})
        result = ProductSchema.from_external(df, "catalog_simulator")
        assert "product_id" in result.columns
        assert result["product_id"].tolist() == ["A001", "A002"]

    def test_to_catalog_simulator(self):
        """ProductSchema maps product_id to asin for catalog_simulator."""
        df = pd.DataFrame({"product_id": ["P001", "P002"]})
        result = ProductSchema.to_external(df, "catalog_simulator")
        assert "asin" in result.columns
        assert result["asin"].tolist() == ["P001", "P002"]


class TestMetricsSchema:
    """Tests for the MetricsSchema instance."""

    def test_required_columns(self):
        """MetricsSchema requires product_id, date, sales_volume, revenue."""
        assert "product_id" in MetricsSchema.required
        assert "date" in MetricsSchema.required
        assert "sales_volume" in MetricsSchema.required
        assert "revenue" in MetricsSchema.required

    def test_optional_columns(self):
        """MetricsSchema has inventory_level, customer_engagement as optional."""
        assert "inventory_level" in MetricsSchema.optional
        assert "customer_engagement" in MetricsSchema.optional

    def test_catalog_simulator_mapping(self):
        """MetricsSchema maps asin and ordered_units for catalog_simulator."""
        df = pd.DataFrame(
            {
                "asin": ["A001"],
                "ordered_units": [100],
                "date": ["2024-01-01"],
                "revenue": [1000.0],
            }
        )
        result = MetricsSchema.from_external(df, "catalog_simulator")
        assert "product_id" in result.columns
        assert "sales_volume" in result.columns
        assert result["product_id"].tolist() == ["A001"]
        assert result["sales_volume"].tolist() == [100]

    def test_validate_complete_dataframe(self):
        """MetricsSchema validates DataFrame with all required columns."""
        df = pd.DataFrame(
            {
                "product_id": ["P001"],
                "date": ["2024-01-01"],
                "sales_volume": [100],
                "revenue": [1000.0],
            }
        )
        assert MetricsSchema.validate(df) is True

    def test_validate_missing_column(self):
        """MetricsSchema raises error when required column missing."""
        df = pd.DataFrame(
            {
                "product_id": ["P001"],
                "date": ["2024-01-01"],
                # missing sales_volume and revenue
            }
        )
        with pytest.raises(ValueError, match="Missing required columns"):
            MetricsSchema.validate(df)
