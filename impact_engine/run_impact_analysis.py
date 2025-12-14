"""
Impact analysis function for the impact_engine package.
"""
import pandas as pd
from typing import Union, List
from .data_sources import DataSourceManager


def evaluate_impact(
    config_path: str, 
    products: Union[List[str], None] = None,
    output_path: str = "impact_analysis_result.csv"
) -> str:
    """
    Evaluate impact using business metrics retrieved through the data abstraction layer.
    """
    
    # Use data abstraction layer
    manager = DataSourceManager()
    config = manager.load_config(config_path)
        
    # Retrieve business metrics using data abstraction layer
    business_metrics = manager.retrieve_metrics(products)
    
    # Perform impact analysis
    impact_results = _perform_impact_analysis(business_metrics)
    
    # Save results to CSV file
    impact_results.to_csv(output_path, index=False)
    
    return output_path


def _perform_impact_analysis(business_metrics: pd.DataFrame) -> pd.DataFrame:
    """Perform impact analysis on the retrieved business metrics."""
    
    if business_metrics.empty:
        return business_metrics
    
    # Add some basic analysis columns as an example
    analysis_results = business_metrics.copy()
    
    # Example: Add a simple impact score based on revenue and sales volume
    if 'revenue' in analysis_results.columns and 'sales_volume' in analysis_results.columns:
        max_revenue = analysis_results['revenue'].max() if analysis_results['revenue'].max() > 0 else 1
        max_sales = analysis_results['sales_volume'].max() if analysis_results['sales_volume'].max() > 0 else 1
        
        analysis_results['impact_score'] = (
            (analysis_results['revenue'] / max_revenue * 0.7) +
            (analysis_results['sales_volume'] / max_sales * 0.3)
        ).round(3)
    
    return analysis_results