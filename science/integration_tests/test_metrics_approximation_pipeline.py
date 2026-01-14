"""Integration tests for metrics approximation with catalog simulator data.

These tests verify the full pipeline:
1. CatalogSimulator provides sales data
2. Enrichment provides quality scores (before/after)
3. Data is aggregated and transformed to cross-sectional format
4. MetricsApproximationAdapter computes impact approximations
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from impact_engine.metrics import CatalogSimulatorAdapter
from impact_engine.models.metrics_approximation import MetricsApproximationAdapter


def create_mock_sales_data() -> pd.DataFrame:
    """Create mock sales data as returned by CatalogSimulator."""
    return pd.DataFrame({
        "asin": ["P001", "P001", "P001", "P002", "P002", "P002", "P003", "P003", "P003"],
        "date": pd.to_datetime([
            "2024-01-01", "2024-01-02", "2024-01-03",
            "2024-01-01", "2024-01-02", "2024-01-03",
            "2024-01-01", "2024-01-02", "2024-01-03",
        ]),
        "ordered_units": [10, 12, 11, 20, 22, 21, 15, 18, 16],
        "revenue": [100.0, 120.0, 110.0, 200.0, 220.0, 210.0, 150.0, 180.0, 160.0],
        "price": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
    })


def create_mock_enrichment_data() -> pd.DataFrame:
    """Create mock enrichment data with quality scores before/after."""
    return pd.DataFrame({
        "product_id": ["P001", "P002", "P003"],
        "quality_before": [0.45, 0.30, 0.55],
        "quality_after": [0.85, 0.75, 0.90],
    })


def aggregate_baseline_sales(sales_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate sales data to get baseline sales per product."""
    # Transform from catalog_simulator format (asin → product_id)
    df = sales_df.copy()
    if "asin" in df.columns:
        df["product_id"] = df["asin"]
    
    # Aggregate revenue per product as baseline
    aggregated = df.groupby("product_id").agg({
        "revenue": "sum"
    }).reset_index()
    aggregated.columns = ["product_id", "baseline_sales"]
    
    return aggregated


def prepare_approximation_input(
    baseline_sales: pd.DataFrame,
    enrichment_data: pd.DataFrame,
) -> pd.DataFrame:
    """Join baseline sales with enrichment quality scores.
    
    Returns DataFrame with columns:
    - product_id
    - quality_before
    - quality_after  
    - baseline_sales
    """
    merged = enrichment_data.merge(baseline_sales, on="product_id", how="inner")
    return merged


class TestMetricsApproximationPipeline:
    """Integration tests for full metrics approximation pipeline."""

    def test_full_pipeline_with_mocked_simulator(self):
        """
        End-to-end test:
        1. Get sales data (mocked)
        2. Get enrichment quality scores (mocked)
        3. Aggregate baseline sales
        4. Prepare cross-sectional input
        5. Run MetricsApproximationAdapter
        6. Verify results
        """
        # Step 1: Get mocked sales data
        sales_data = create_mock_sales_data()
        
        # Step 2: Get mocked enrichment data
        enrichment_data = create_mock_enrichment_data()
        
        # Step 3: Aggregate baseline sales
        baseline_sales = aggregate_baseline_sales(sales_data)
        
        # Verify aggregation
        assert len(baseline_sales) == 3
        assert baseline_sales[baseline_sales["product_id"] == "P001"]["baseline_sales"].iloc[0] == 330.0
        assert baseline_sales[baseline_sales["product_id"] == "P002"]["baseline_sales"].iloc[0] == 630.0
        assert baseline_sales[baseline_sales["product_id"] == "P003"]["baseline_sales"].iloc[0] == 490.0
        
        # Step 4: Prepare cross-sectional input
        approximation_input = prepare_approximation_input(baseline_sales, enrichment_data)
        
        assert len(approximation_input) == 3
        assert all(col in approximation_input.columns for col in [
            "product_id", "quality_before", "quality_after", "baseline_sales"
        ])
        
        # Step 5: Run MetricsApproximationAdapter
        adapter = MetricsApproximationAdapter()
        adapter.connect({
            "metric_before_column": "quality_before",
            "metric_after_column": "quality_after",
            "baseline_column": "baseline_sales",
            "response": {
                "FUNCTION": "linear",
                "PARAMS": {"coefficient": 0.5}
            }
        })
        
        results = adapter.fit(approximation_input)
        
        # Step 6: Verify results
        assert results["model_type"] == "metrics_approximation"
        assert results["response_function"] == "linear"
        assert results["impact_estimates"]["n_products"] == 3
        
        # Verify per-product calculations
        per_product = {p["product_id"]: p for p in results["per_product"]}
        
        # P001: delta = 0.85 - 0.45 = 0.4, impact = 0.4 * 330 * 0.5 = 66.0
        assert per_product["P001"]["delta_metric"] == 0.4
        assert per_product["P001"]["approximated_impact"] == 66.0
        
        # P002: delta = 0.75 - 0.30 = 0.45, impact = 0.45 * 630 * 0.5 = 141.75
        assert per_product["P002"]["delta_metric"] == 0.45
        assert per_product["P002"]["approximated_impact"] == 141.75
        
        # P003: delta = 0.90 - 0.55 = 0.35, impact = 0.35 * 490 * 0.5 = 85.75
        assert per_product["P003"]["delta_metric"] == 0.35
        assert per_product["P003"]["approximated_impact"] == 85.75
        
        # Verify totals
        expected_total = 66.0 + 141.75 + 85.75
        assert results["impact_estimates"]["total_approximated_impact"] == expected_total

    def test_catalog_simulator_transform_and_approximate(self, tmp_path):
        """
        Test using CatalogSimulatorAdapter's transform_inbound to 
        convert data format, then run approximation.
        """
        # Create adapter for data transformation
        simulator_adapter = CatalogSimulatorAdapter()
        simulator_adapter.connect({"mode": "rule", "seed": 42})
        
        # Mock raw sales data from simulator
        raw_sales = create_mock_sales_data()
        
        # Transform using adapter's transform_inbound
        standardized_sales = simulator_adapter.transform_inbound(raw_sales)
        
        # Verify transformation
        assert "product_id" in standardized_sales.columns  # asin → product_id
        assert "sales_volume" in standardized_sales.columns  # ordered_units → sales_volume
        
        # Aggregate and prepare for approximation
        baseline = standardized_sales.groupby("product_id").agg({
            "revenue": "sum"
        }).reset_index()
        baseline.columns = ["product_id", "baseline_sales"]
        
        # Add quality scores
        enrichment = create_mock_enrichment_data()
        input_data = enrichment.merge(baseline, on="product_id")
        
        # Run approximation
        approximation_adapter = MetricsApproximationAdapter()
        approximation_adapter.connect({
            "response": {"FUNCTION": "linear", "PARAMS": {"coefficient": 1.0}}
        })
        
        results = approximation_adapter.fit(input_data)
        
        # Verify
        assert results["impact_estimates"]["n_products"] == 3
        assert results["impact_estimates"]["total_approximated_impact"] > 0

    def test_coefficient_sensitivity(self):
        """Test that different coefficients produce proportionally different impacts."""
        sales_data = create_mock_sales_data()
        enrichment_data = create_mock_enrichment_data()
        baseline_sales = aggregate_baseline_sales(sales_data)
        input_data = prepare_approximation_input(baseline_sales, enrichment_data)
        
        # Run with coefficient 0.5
        adapter1 = MetricsApproximationAdapter()
        adapter1.connect({
            "response": {"FUNCTION": "linear", "PARAMS": {"coefficient": 0.5}}
        })
        results1 = adapter1.fit(input_data)
        
        # Run with coefficient 1.0
        adapter2 = MetricsApproximationAdapter()
        adapter2.connect({
            "response": {"FUNCTION": "linear", "PARAMS": {"coefficient": 1.0}}
        })
        results2 = adapter2.fit(input_data)
        
        # Coefficient 1.0 should produce 2x the impact of coefficient 0.5
        ratio = (
            results2["impact_estimates"]["total_approximated_impact"] /
            results1["impact_estimates"]["total_approximated_impact"]
        )
        assert abs(ratio - 2.0) < 0.01

    def test_empty_enrichment_raises_error(self):
        """Test that empty enrichment data raises appropriate error."""
        adapter = MetricsApproximationAdapter()
        adapter.connect({
            "response": {"FUNCTION": "linear"}
        })
        
        empty_data = pd.DataFrame(columns=[
            "product_id", "quality_before", "quality_after", "baseline_sales"
        ])
        
        with pytest.raises(ValueError, match="validation failed"):
            adapter.fit(empty_data)

    def test_missing_quality_columns_raises_error(self):
        """Test that missing quality columns raises appropriate error."""
        adapter = MetricsApproximationAdapter()
        adapter.connect({
            "response": {"FUNCTION": "linear"}
        })
        
        # Missing quality_after column
        incomplete_data = pd.DataFrame({
            "product_id": ["P001"],
            "quality_before": [0.5],
            "baseline_sales": [100.0],
        })
        
        with pytest.raises(ValueError, match="validation failed"):
            adapter.fit(incomplete_data)
