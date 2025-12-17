"""
Workflow script using the data abstraction layer for impact analysis.
"""

from online_retail_simulator import simulate_characteristics
from impact_engine import evaluate_impact


if __name__ == "__main__":
	
	config_path = "config_simulator.yaml"
	products_df = simulate_characteristics(config_path)
	

	config_path = "config_impact_engine.yaml"
	result_path = evaluate_impact(config_path, products_df)
	