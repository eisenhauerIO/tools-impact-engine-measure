"""
Workflow script using the data abstraction layer for impact analysis.
"""

import os

import yaml
from impact_engine import evaluate_impact
from online_retail_simulator import simulate_characteristics

if __name__ == "__main__":
    # Step 1: Simulate product characteristics
    config_path = "config_catalog_simulator.yaml"
    job_info = simulate_characteristics(config_path)

    # Step 2: Load products from job and save to CSV
    products = job_info.load_df("products")
    os.makedirs("output", exist_ok=True)
    products_path = "output/products.csv"
    products.to_csv(products_path, index=False)

    # Step 3: Update impact engine config with products path
    with open("config_impact_engine.yaml", "r") as f:
        impact_config = yaml.safe_load(f)
    impact_config["DATA"]["PATH"] = products_path
    impact_config["DATA"]["SOURCE"]["CONFIG"]["PATH"] = products_path
    with open("config_impact_engine.yaml", "w") as f:
        yaml.dump(impact_config, f, default_flow_style=False)

    # Step 4: Run impact evaluation
    config_path = "config_impact_engine.yaml"
    result_path = evaluate_impact(config_path)
