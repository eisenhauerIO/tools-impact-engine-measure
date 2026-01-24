"""Demo: Metrics-based impact approximation using evaluate_impact().

This demo shows the typical usage pattern:
1. User provides products.csv
2. User provides config.yaml with DATA.ENRICHMENT section
3. User calls evaluate_impact(config.yaml)
4. Engine handles everything internally (adapter, enrichment, transform, model)

Output: Impact approximation results
"""

import json
import tempfile
from pathlib import Path

import yaml
from impact_engine import evaluate_impact

# Config file for this demo
CONFIG_PATH = Path(__file__).parent / "config_metrics_approximation_workflow.yaml"


def create_products_csv(output_path: str) -> str:
    """Create products.csv using catalog simulator.

    In production, this would be your actual product catalog.
    """
    from online_retail_simulator.simulate import simulate_characteristics

    sim_config = {
        "STORAGE": {"PATH": str(Path(output_path) / "simulation")},
        "RULE": {
            "CHARACTERISTICS": {
                "FUNCTION": "simulate_characteristics_rule_based",
                "PARAMS": {"num_products": 5},
            },
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(sim_config, f)
        sim_config_path = f.name

    job_info = simulate_characteristics(sim_config_path)
    products = job_info.load_df("products")

    products_path = Path(output_path) / "products.csv"
    products.to_csv(products_path, index=False)
    print(f"   Created: {products_path}")
    print(f"   Products: {len(products)}")

    return str(products_path)


def run_demo():
    """Run the metrics approximation demo using evaluate_impact()."""
    print("=" * 60)
    print("Metrics-Based Impact Approximation Demo")
    print("Using evaluate_impact() - single call does everything!")
    print("=" * 60)

    # Create output directory
    output_path = Path("output/demo_metrics_approximation")
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. Create products.csv
    print("\n1. Creating products.csv:")
    create_products_csv(str(output_path))

    # 2. Load and display config
    print(f"\n2. Using config: {CONFIG_PATH}")
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)
    print(f"   ENRICHMENT: {config['DATA']['ENRICHMENT']['FUNCTION']}")
    print(f"   TRANSFORM: {config['DATA']['TRANSFORM']['FUNCTION']}")
    print(f"   MODEL: {config['MEASUREMENT']['MODEL']}")

    # 3. Call evaluate_impact() - single call does everything!
    print("\n3. Calling evaluate_impact()...")
    print("   - Engine creates CatalogSimulatorAdapter")
    print("   - Adapter simulates metrics")
    print("   - Adapter generates product_details")
    print("   - Adapter applies enrichment (quality boost)")
    print("   - Transform extracts quality_before/quality_after")
    print("   - MetricsApproximationAdapter computes impact")

    results_path = evaluate_impact(str(CONFIG_PATH), str(output_path / "results"))

    # Load results from the JSON file
    with open(results_path) as f:
        results = json.load(f)

    # 4. Display results
    print("\n4. Results:")
    print("-" * 60)

    print(f"\n   Model Type: {results['model_type']}")
    print(f"   Response Function: {results['response_function']}")

    estimates = results["impact_estimates"]
    print("\n   Aggregate Impact Estimates:")
    print(f"   - Total Approximated Impact: ${estimates['total_approximated_impact']:.2f}")
    print(f"   - Mean Approximated Impact:  ${estimates['mean_approximated_impact']:.2f}")
    print(f"   - Mean Quality Change:       {estimates['mean_metric_change']:.4f}")
    print(f"   - Number of Products:        {estimates['n_products']}")

    print("\n   Per-Product Breakdown:")
    print("   " + "-" * 56)
    print(f"   {'Product':<15} {'Δ Quality':<12} {'Baseline':<12} {'Impact':<12}")
    print("   " + "-" * 56)
    for p in results["per_product"]:
        print(
            f"   {p['product_id']:<15} {p['delta_metric']:<12.4f} "
            f"${p['baseline_outcome']:<11.2f} ${p['approximated_impact']:<11.2f}"
        )

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print(f"Results saved to: {results_path}")
    print("=" * 60)

    return results


if __name__ == "__main__":
    run_demo()
