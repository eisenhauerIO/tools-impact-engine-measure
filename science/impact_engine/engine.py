"""
Impact analysis engine for the impact_engine package.
"""
import pandas as pd
from .metrics import MetricsManager
from .models import ModelsManager
from .config import parse_config_file
from artifact_store import create_job


def evaluate_impact(
    config_path: str,
    storage_url: str = "./data"
) -> str:
    """
    Evaluate impact using business metrics retrieved through the metrics layer
    and models layer for statistical analysis.

    Args:
        config_path: Path to configuration file containing metrics and model settings.
                     The config must include DATA.PATH pointing to a products CSV file.
        storage_url: Storage URL or path (e.g., "./data", "s3://bucket/prefix")

    Returns:
        str: URL to the saved model results (within the job directory)
    """
    # Parse config to get paths
    config = parse_config_file(config_path)
    data_path = config["DATA"]["PATH"]
    output_path = config.get("OUTPUT", {}).get("PATH", "results")

    # Create parent job for this impact analysis run
    job = create_job(output_path, prefix="job-impact-engine")
    job_store = job.get_store()

    # Save original config to job directory for observability
    job_store.write_yaml("config.yaml", config)

    # Load products from CSV
    products = pd.read_csv(data_path)

    # Initialize components with parent job
    # Adapters will create nested jobs inside the parent job directory
    metrics_manager = MetricsManager.from_config_file(config_path, parent_job=job)
    models_manager = ModelsManager.from_config_file(config_path)

    # Retrieve business metrics using metrics layer
    business_metrics = metrics_manager.retrieve_metrics(products)

    # Aggregate metrics by date for time series analysis
    # Sum numeric columns, keep date
    numeric_cols = business_metrics.select_dtypes(include=['number']).columns.tolist()
    aggregated_metrics = business_metrics.groupby('date')[numeric_cols].sum().reset_index()

    # Fit model using models manager with job store
    # fit_model returns the full path to the results file
    model_results_path = models_manager.fit_model(
        data=aggregated_metrics,
        output_path="results",
        storage=job_store
    )

    return model_results_path