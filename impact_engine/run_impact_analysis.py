"""
Impact analysis function for the impact_engine package.
"""
import pandas as pd
from typing import Optional
from pathlib import Path
from .metrics import MetricsManager
from .models import ModelsManager


def evaluate_impact(
    config_path: str, 
    products: Optional[pd.DataFrame] = None,
    output_path: str = "impact_analysis_result.csv"
) -> str:
    """
    Evaluate impact using business metrics retrieved through the metrics layer
    and models layer for statistical analysis.
    
    This function integrates the metrics layer with the models layer to:
    1. Retrieve business metrics for specified products
    2. Fit statistical models to measure causal impact
    3. Return results from the models analysis
    
    Args:
        config_path: Path to configuration file containing metrics and model settings
        products: DataFrame containing product identifiers and characteristics (optional)
        output_path: Directory path where model results should be saved
    
    Returns:
        str: Path to the saved model results file
    """
    
    # Initialize components with their respective config blocks
    metrics_manager = MetricsManager.from_config_file(config_path)
    models_manager = ModelsManager.from_config_file(config_path)
    
    # Retrieve business metrics using metrics layer
    business_metrics = metrics_manager.retrieve_metrics(products)
    
    # Fit model using models manager (parameters come from config)
    model_results_path = models_manager.fit_model(
        data=business_metrics,
        output_path=output_path
    )
    
    return model_results_path
