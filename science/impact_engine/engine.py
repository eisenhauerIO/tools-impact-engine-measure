"""
Impact analysis engine for the impact_engine package.
"""
import pandas as pd
from typing import Optional
from .metrics import MetricsManager
from .models import ModelsManager
from artefact_store import create_artefact_store


def evaluate_impact(
    config_path: str, 
    products: Optional[pd.DataFrame] = None,
    storage_url: str = "./data",
    tenant_id: str = "default"
) -> str:
    """
    Evaluate impact using business metrics retrieved through the metrics layer
    and models layer for statistical analysis.
    
    Args:
        config_path: Path to configuration file containing metrics and model settings
        products: DataFrame containing product identifiers and characteristics (optional)
        storage_url: Storage URL or path (e.g., "./data", "s3://bucket/prefix")
        tenant_id: Tenant identifier for multi-tenant isolation
    
    Returns:
        str: URL to the saved model results
    """
    
    # Create artefact store backend
    artefact_store = create_artefact_store(storage_url)
    
    # Initialize components with storage and tenant context
    metrics_manager = MetricsManager.from_config_file(config_path)
    models_manager = ModelsManager.from_config_file(config_path)
    
    # Retrieve business metrics using metrics layer
    business_metrics = metrics_manager.retrieve_metrics(products)
    
    # Fit model using models manager with artefact store
    model_results_path = models_manager.fit_model(
        data=business_metrics,
        output_path="results",
        storage=artefact_store,
        tenant_id=tenant_id
    )
    
    return model_results_path