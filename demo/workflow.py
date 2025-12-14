"""
Workflow script using the data abstraction layer for impact analysis.
"""

from online_retail_simulator import simulate_characteristics
from impact_engine import evaluate_impact


if __name__ == "__main__":
	# Get product characteristics to determine which products to analyze
	config_path = "config_simulator.json"
	products_df = simulate_characteristics(config_path)
	
	# Extract product IDs for the new data abstraction layer approach
	product_ids = products_df['product_id'].tolist()
	print(f"Analyzing {len(product_ids)} products: {product_ids[:5]}...")
	
	# Use the data abstraction layer for impact analysis
	result_path = evaluate_impact("config_request.json", product_ids)
	print(f"Analysis result saved to: {result_path}")