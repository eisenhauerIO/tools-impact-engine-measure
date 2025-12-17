"""
Impact analysis function for the impact_engine package.
"""
import pandas as pd
from typing import Union, List
from pathlib import Path
from .data_sources import DataSourceManager
from .modeling import ModelingEngine, InterruptedTimeSeriesModel


def evaluate_impact(
    config_path: str, 
    products: Union[List[str], None] = None,
    output_path: str = "impact_analysis_result.csv"
) -> str:
    """
    Evaluate impact using business metrics retrieved through the data abstraction layer
    and modeling layer for statistical analysis.
    
    This function integrates the data abstraction layer with the modeling layer to:
    1. Retrieve business metrics for specified products
    2. Fit statistical models to measure causal impact
    3. Return results from the modeling analysis
    
    Args:
        config_path: Path to configuration file containing data source and model settings
        products: List of product IDs to analyze (optional)
        output_path: Directory path where model results should be saved
    
    Returns:
        str: Path to the saved model results file
    """
    
    # Use data abstraction layer to retrieve business metrics
    manager = DataSourceManager()
    config = manager.load_config(config_path)
    

    # Retrieve business metrics using data abstraction layer
    business_metrics = manager.retrieve_metrics(products)

    # Initialize modeling engine and register models
    modeling_engine = ModelingEngine()
    modeling_engine.register_model("interrupted_time_series", InterruptedTimeSeriesModel)
    
    # Load modeling configuration
    modeling_engine.load_config(config_path)
    
    # Extract intervention date from configuration
    measurement_config = config.get("MEASUREMENT", {})
    params = measurement_config.get("PARAMS", {})
    intervention_date = params.get("INTERVENTION_DATE")
    dependent_variable = params.get("DEPENDENT_VARIABLE", "revenue")
    
    if not intervention_date:
        raise ValueError("INTERVENTION_DATE must be specified in MEASUREMENT.PARAMS configuration")
    
    # Create output directory if it doesn't exist
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Fit model using modeling engine
    model_results_path = modeling_engine.fit_model(
        data=business_metrics,
        intervention_date=intervention_date,
        output_path=str(output_dir),
        dependent_variable=dependent_variable
    )
    
    return model_results_path
