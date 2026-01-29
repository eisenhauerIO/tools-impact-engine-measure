"""
Impact analysis engine for the impact_engine package.
"""

import pandas as pd

from .config import parse_config_file
from .core import apply_transform
from .metrics import create_metrics_manager
from .models import create_models_manager
from .storage import create_storage_manager


def evaluate_impact(config_path: str, storage_url: str = "./data") -> str:
    """
    Evaluate impact using business metrics retrieved through the metrics layer
    and models layer for statistical analysis.

    Args:
        config_path: Path to configuration file containing metrics and model settings.
                     The config must include DATA.SOURCE.CONFIG.PATH pointing to a products CSV file.
        storage_url: Storage URL or path (e.g., "./data", "s3://bucket/prefix")

    Returns:
        str: URL to the saved model results (within the job directory)
    """
    config = parse_config_file(config_path)
    source_config = config["DATA"]["SOURCE"]["CONFIG"]
    transform_config = config["DATA"]["TRANSFORM"]
    data_path = source_config["path"]

    # Create storage manager (storage_url allows tests to pass temp directories)
    storage_manager = create_storage_manager(storage_url)

    # Save artifacts for observability
    storage_manager.write_yaml("config.yaml", config)
    products = pd.read_csv(data_path)
    storage_manager.write_csv("products.csv", products)

    metrics_manager = create_metrics_manager(config, parent_job=storage_manager.get_job())
    models_manager = create_models_manager(config_path)

    business_metrics = metrics_manager.retrieve_metrics(products)
    storage_manager.write_csv("business_metrics.csv", business_metrics)

    transformed_metrics = apply_transform(business_metrics, transform_config)
    storage_manager.write_csv("transformed_metrics.csv", transformed_metrics)

    model_results_path = models_manager.fit_model(
        data=transformed_metrics, output_path="results", storage=storage_manager
    )

    return model_results_path
