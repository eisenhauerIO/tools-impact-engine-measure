"""Demo: Metrics-based impact approximation with simulated data.

This demo shows how to use the MetricsApproximationAdapter to estimate
treatment impact based on quality score changes.

Input: DataFrame of enriched products with before/after quality scores
       and baseline sales (simulating data from catalog-generator).

Output: Per-product and aggregate impact approximations.
"""

import pandas as pd

from impact_engine.models.metrics_approximation import MetricsApproximationAdapter


def create_simulated_data() -> pd.DataFrame:
    """Create simulated data representing enriched products.
    
    In production, this data would come from catalog-generator's
    enrichment process. Here we simulate 5 products that received
    quality improvements through enrichment.
    
    Returns:
        DataFrame with columns:
        - product_id: Product identifier
        - quality_before: Quality score before enrichment (0.0-1.0)
        - quality_after: Quality score after enrichment (0.0-1.0)
        - baseline_sales: Historical baseline sales/revenue
    """
    return pd.DataFrame({
        "product_id": ["P001", "P002", "P003", "P004", "P005"],
        "quality_before": [0.45, 0.30, 0.55, 0.40, 0.35],
        "quality_after": [0.85, 0.75, 0.90, 0.80, 0.70],
        "baseline_sales": [100.0, 150.0, 200.0, 120.0, 180.0],
    })


def run_demo():
    """Run the metrics approximation demo."""
    print("=" * 60)
    print("Metrics-Based Impact Approximation Demo")
    print("=" * 60)
    
    # 1. Create simulated data
    print("\n1. Simulated Input Data (enriched products only):")
    data = create_simulated_data()
    print(data.to_string(index=False))
    
    # 2. Configure the model
    print("\n2. Model Configuration:")
    config = {
        "metric_before_column": "quality_before",
        "metric_after_column": "quality_after",
        "baseline_column": "baseline_sales",
        "response": {
            "FUNCTION": "linear",
            "PARAMS": {"coefficient": 0.5}
        }
    }
    print(f"   - Response Function: {config['response']['FUNCTION']}")
    print(f"   - Coefficient: {config['response']['PARAMS']['coefficient']}")
    print("   - Formula: impact = coefficient × Δ_quality × baseline_sales")
    
    # 3. Initialize and connect adapter
    adapter = MetricsApproximationAdapter()
    adapter.connect(config)
    print("\n3. Model initialized and connected successfully.")
    
    # 4. Run approximation
    print("\n4. Running impact approximation...")
    results = adapter.fit(data)
    
    # 5. Display results
    print("\n5. Results:")
    print("-" * 60)
    
    print("\n   Aggregate Impact Estimates:")
    estimates = results["impact_estimates"]
    print(f"   - Total Approximated Impact: ${estimates['total_approximated_impact']:.2f}")
    print(f"   - Mean Approximated Impact:  ${estimates['mean_approximated_impact']:.2f}")
    print(f"   - Mean Quality Change:       {estimates['mean_metric_change']:.4f}")
    print(f"   - Number of Products:        {estimates['n_products']}")
    
    print("\n   Per-Product Breakdown:")
    print("   " + "-" * 56)
    print(f"   {'Product':<10} {'Δ Quality':<12} {'Baseline':<12} {'Impact':<12}")
    print("   " + "-" * 56)
    for p in results["per_product"]:
        print(f"   {p['product_id']:<10} {p['delta_metric']:<12.4f} ${p['baseline_outcome']:<11.2f} ${p['approximated_impact']:<11.2f}")
    
    # 6. Explain calculation
    print("\n6. Example Calculation (P001):")
    p1 = results["per_product"][0]
    print(f"   Δ_quality = {data.iloc[0]['quality_after']} - {data.iloc[0]['quality_before']} = {p1['delta_metric']}")
    print(f"   impact = 0.5 × {p1['delta_metric']} × ${p1['baseline_outcome']:.0f} = ${p1['approximated_impact']:.2f}")
    
    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    
    return results


if __name__ == "__main__":
    run_demo()
