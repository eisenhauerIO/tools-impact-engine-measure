"""
Basic impact analysis function for the impact_engine package.
"""
import pandas as pd

def evaluate_impact(config_path, products):
    """
    Dummy implementation: Save products DataFrame to a CSV file and return the path.
    Args:
        config_path (str): Path to the config file (unused in this stub).
        products (pd.DataFrame): DataFrame of simulated products.
    Returns:
        str: Path to the saved CSV file.
    """
    output_path = "impact_analysis_result.csv"
    products.to_csv(output_path, index=False)
    return output_path
