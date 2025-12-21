"""
Enrichment Recovery Demo - Validates ITS model using factual vs counterfactual comparison.

This demo:
1. Generates baseline sales (counterfactual - what would happen without enrichment)
2. Applies enrichment to get factual sales (what actually happens with enrichment)
3. Calculates TRUE effect by comparing factual vs counterfactual
4. Runs ITS analysis to ESTIMATE the effect from factual data alone
5. Compares ITS estimate to true effect to validate the model
"""

import json
import os
import pandas as pd
import yaml
from online_retail_simulator import simulate_characteristics
from impact_engine import evaluate_impact
from impact_engine.metrics import MetricsManager

# Fixed products path for reproducible results
FIXED_PRODUCTS_PATH = "output/fixed_products.csv"


def calculate_true_effect(
    baseline_metrics: pd.DataFrame,
    enriched_metrics: pd.DataFrame,
    intervention_date: str,
    metric: str = "sales_volume"
) -> dict:
    """
    Calculate the TRUE causal effect by comparing factual vs counterfactual.

    Args:
        baseline_metrics: Counterfactual data (no enrichment)
        enriched_metrics: Factual data (with enrichment)
        intervention_date: When enrichment started
        metric: Which metric to analyze

    Returns:
        dict with true effect statistics
    """
    intervention = pd.Timestamp(intervention_date)

    # Aggregate by date
    baseline_daily = baseline_metrics.groupby('date')[metric].sum().reset_index()
    enriched_daily = enriched_metrics.groupby('date')[metric].sum().reset_index()
    baseline_daily['date'] = pd.to_datetime(baseline_daily['date'])
    enriched_daily['date'] = pd.to_datetime(enriched_daily['date'])

    # Post-intervention comparison (factual vs counterfactual)
    baseline_post = baseline_daily[baseline_daily['date'] >= intervention][metric]
    enriched_post = enriched_daily[enriched_daily['date'] >= intervention][metric]

    baseline_mean = baseline_post.mean()
    enriched_mean = enriched_post.mean()
    absolute_effect = enriched_mean - baseline_mean
    percent_effect = (absolute_effect / baseline_mean * 100) if baseline_mean > 0 else 0

    return {
        "counterfactual_mean": float(baseline_mean),
        "factual_mean": float(enriched_mean),
        "absolute_effect": float(absolute_effect),
        "percent_effect": float(percent_effect),
    }


def print_comparison(true_effect: dict, its_result_path: str, metric: str) -> None:
    """Print comparison of true effect vs ITS estimate."""
    # Load ITS results
    with open(its_result_path, "r") as f:
        its_results = json.load(f)

    impact_estimates = its_results.get("impact_estimates", {})
    its_pct = impact_estimates.get("percent_change", 0)
    true_pct = true_effect["percent_effect"]

    # Calculate recovery accuracy
    if true_pct != 0:
        recovery_accuracy = (1 - abs(1 - its_pct / true_pct)) * 100
    else:
        recovery_accuracy = 100 if its_pct == 0 else 0

    print("\n" + "=" * 65)
    print("ENRICHMENT RECOVERY VALIDATION")
    print("=" * 65)

    print(f"\nMetric analyzed: {metric}")

    print("\n--- True Effect (Factual vs Counterfactual) ---")
    print(f"  Counterfactual mean (no enrichment): {true_effect['counterfactual_mean']:,.1f}")
    print(f"  Factual mean (with enrichment):      {true_effect['factual_mean']:,.1f}")
    print(f"  True causal effect:                  {true_effect['percent_effect']:.1f}%")

    print("\n--- ITS Model Estimate (from factual data only) ---")
    print(f"  Pre-intervention mean:  {impact_estimates.get('pre_intervention_mean', 0):,.1f}")
    print(f"  Post-intervention mean: {impact_estimates.get('post_intervention_mean', 0):,.1f}")
    print(f"  Estimated effect:       {its_pct:.1f}%")

    print("\n--- Model Validation ---")
    print(f"  True effect:       {true_pct:.1f}%")
    print(f"  ITS estimate:      {its_pct:.1f}%")
    print(f"  Recovery accuracy: {max(0, recovery_accuracy):.1f}%")

    model_summary = its_results.get("model_summary", {})
    print(f"\n  Observations: {model_summary.get('n_observations', 'N/A')} days")
    print(f"  Pre-period:   {model_summary.get('pre_period_length', 'N/A')} days")
    print(f"  Post-period:  {model_summary.get('post_period_length', 'N/A')} days")

    print("\n" + "=" * 65)
    if recovery_accuracy >= 90:
        print("EXCELLENT: ITS model accurately recovered the true causal effect!")
    elif recovery_accuracy >= 70:
        print("GOOD: ITS estimate is close to the true effect.")
    elif recovery_accuracy >= 50:
        print("PARTIAL: ITS estimate differs from true effect.")
    else:
        print("WARNING: ITS estimate differs significantly from true effect.")
    print("=" * 65 + "\n")


if __name__ == "__main__":

    # Step 1: Get or generate product characteristics
    if os.path.exists(FIXED_PRODUCTS_PATH):
        print("\nStep 1: Using existing products file...")
        products_path = FIXED_PRODUCTS_PATH
    else:
        print("\nStep 1: Generating product characteristics (first run)...")
        import shutil
        job_info = simulate_characteristics("config_enrichment_simulator.yaml")
        src_path = f"{job_info.full_path}/products.csv"
        os.makedirs(os.path.dirname(FIXED_PRODUCTS_PATH), exist_ok=True)
        shutil.copy(src_path, FIXED_PRODUCTS_PATH)
        products_path = FIXED_PRODUCTS_PATH
        print(f"  Saved to: {products_path}")

    # Load config
    with open("config_enrichment.yaml", "r") as f:
        config = yaml.safe_load(f)
    config["DATA"]["PATH"] = products_path

    enrichment_config = config["DATA"]["ENRICHMENT"]
    intervention_date = enrichment_config["params"]["enrichment_start"]
    effect_size = enrichment_config["params"]["effect_size"]
    metric = config["MEASUREMENT"]["PARAMS"]["DEPENDENT_VARIABLE"]

    print(f"  Products: {products_path}")
    print(f"  Enrichment: {effect_size*100:.0f}% boost starting {intervention_date}")
    print(f"  Metric: {metric}")

    # Step 2: Get BASELINE metrics (counterfactual - no enrichment)
    print("\nStep 2: Generating counterfactual (no enrichment)...")
    products = pd.read_csv(products_path)

    # Create config without enrichment
    baseline_config = config.copy()
    baseline_config["DATA"] = {k: v for k, v in config["DATA"].items() if k != "ENRICHMENT"}
    baseline_config["DATA"]["PATH"] = products_path

    with open("_temp_baseline.yaml", "w") as f:
        yaml.dump(baseline_config, f)

    baseline_manager = MetricsManager.from_config_file("_temp_baseline.yaml")
    baseline_metrics = baseline_manager.retrieve_metrics(products)
    os.remove("_temp_baseline.yaml")
    print(f"  Generated {len(baseline_metrics)} baseline records")

    # Step 3: Get ENRICHED metrics (factual - with enrichment)
    print("\nStep 3: Generating factual (with enrichment)...")
    with open("config_enrichment.yaml", "w") as f:
        yaml.dump(config, f)

    enriched_manager = MetricsManager.from_config_file("config_enrichment.yaml")
    enriched_metrics = enriched_manager.retrieve_metrics(products)
    print(f"  Generated {len(enriched_metrics)} enriched records")

    # Step 4: Calculate TRUE effect (factual vs counterfactual)
    print("\nStep 4: Calculating true causal effect...")
    true_effect = calculate_true_effect(
        baseline_metrics, enriched_metrics, intervention_date, metric
    )
    print(f"  True effect: {true_effect['percent_effect']:.1f}%")

    # Step 5: Run ITS on factual data
    print("\nStep 5: Running ITS model on factual data...")
    result_path = evaluate_impact("config_enrichment.yaml")
    print(f"  Results: {result_path}")

    # Step 6: Compare
    print("\nStep 6: Comparing true effect vs ITS estimate...")
    print_comparison(true_effect, result_path, metric)
