"""
Impact analysis engine for the impact_engine package.
"""

import pandas as pd
from artifact_store import create_job

from .config import (
    get_source_config,
    get_transform_config,
    parse_config_file,
)
from .core import apply_transform
from .metrics import create_metrics_manager_from_source_config
from .models import create_models_manager


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
    # Parse config to get paths
    config = parse_config_file(config_path)
    source_config = get_source_config(config)
    transform_config = get_transform_config(config)
    data_path = source_config["path"]

    # Create parent job for this impact analysis run
    # Uses storage_url parameter to allow tests to pass temp directories
    job = create_job(storage_url, prefix="job-impact-engine")
    job_store = job.get_store()

    # Save original config to job directory for observability
    job_store.write_yaml("config.yaml", config)

    # Load products from CSV
    products = pd.read_csv(data_path)
    job_store.write_csv("products.csv", products)

    # Initialize components using factory functions
    # Factories handle adapter/model selection based on configuration
    metrics_manager = create_metrics_manager_from_source_config(config, parent_job=job)
    models_manager = create_models_manager(config_path)

    # Retrieve business metrics using metrics layer
    business_metrics = metrics_manager.retrieve_metrics(products)
    job_store.write_csv("business_metrics.csv", business_metrics)

    # Apply configured transform to business metrics
    transformed_metrics = apply_transform(business_metrics, transform_config)
    job_store.write_csv("transformed_metrics.csv", transformed_metrics)

    # Fit model using models manager with job store
    # fit_model returns the full path to the results file
    model_results_path = models_manager.fit_model(
        data=transformed_metrics, output_path="results", storage=job_store
    )

    return model_results_path
