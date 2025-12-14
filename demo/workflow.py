"""
Workflow script to simulate product characteristics and save output.
Reuses existing config structure and OUTPUT section for file path.
"""

import pandas as pd
from online_retail_simulator import simulate_characteristics
from impact_engine import evaluate_impact




if __name__ == "__main__":
	config_path = "config_simulator.json"
	products = simulate_characteristics(config_path)

	result_path = evaluate_impact("config_request.json", products)
	print(f"Analysis result saved to: {result_path}")



