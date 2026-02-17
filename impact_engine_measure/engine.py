"""
Impact analysis engine for the impact_engine_measure package.
"""

from datetime import datetime, timezone
from typing import Optional

from artifact_store import ArtifactStore, JobInfo

from .config import parse_config_file
from .core import apply_transform
from .metrics import create_metrics_manager
from .models import create_models_manager
from .models.base import SCHEMA_VERSION
from .storage import create_storage_manager


def evaluate_impact(
    config_path: str,
    storage_url: str = "./data",
    job_id: Optional[str] = None,
) -> JobInfo:
    """
    Evaluate impact using business metrics retrieved through the metrics layer
    and models layer for statistical analysis.

    Args:
        config_path: Path to configuration file containing metrics and model settings.
                     The config must include DATA.SOURCE.CONFIG.PATH pointing to a products CSV file.
        storage_url: Storage URL or path (e.g., "./data", "s3://bucket/prefix")
        job_id: Optional job ID for resuming existing jobs or using custom IDs.
            If not provided, a unique ID will be auto-generated.

    Returns:
        JobInfo: Job object for the completed run. Use ``load_results(job_info)``
            to load all artifacts into a typed ``MeasureJobResult``.
    """
    config = parse_config_file(config_path)
    source_config = config["DATA"]["SOURCE"]["CONFIG"]
    transform_config = config["DATA"]["TRANSFORM"]
    data_path = source_config["path"]

    # Create storage manager (storage_url allows tests to pass temp directories)
    storage_manager = create_storage_manager(storage_url, job_id=job_id)

    # Save artifacts for observability
    storage_manager.write_yaml("config.yaml", config)
    data_store, data_filename = ArtifactStore.from_file_path(data_path)
    products = data_store.read_data(data_filename)
    storage_manager.write_parquet("products.parquet", products)

    metrics_manager = create_metrics_manager(config, parent_job=storage_manager.get_job())
    models_manager = create_models_manager(config_path)

    business_metrics = metrics_manager.retrieve_metrics(products)
    storage_manager.write_parquet("business_metrics.parquet", business_metrics)

    transformed_metrics = apply_transform(business_metrics, transform_config)
    storage_manager.write_parquet("transformed_metrics.parquet", transformed_metrics)

    fit_output = models_manager.fit_model(data=transformed_metrics, storage=storage_manager)

    # Write manifest as the final step (R3: self-describing output)
    pipeline_files = {
        "config": {"path": "config.yaml", "format": "yaml"},
        "products": {"path": "products.parquet", "format": "parquet"},
        "business_metrics": {"path": "business_metrics.parquet", "format": "parquet"},
        "transformed_metrics": {
            "path": "transformed_metrics.parquet",
            "format": "parquet",
        },
        "impact_results": {"path": "impact_results.json", "format": "json"},
    }

    # Add model-specific artifacts
    for name, full_path in fit_output.artifact_paths.items():
        filename = f"{fit_output.model_type}__{name}.parquet"
        pipeline_files[f"{fit_output.model_type}__{name}"] = {
            "path": filename,
            "format": "parquet",
        }

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "model_type": fit_output.model_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": pipeline_files,
    }
    storage_manager.write_json("manifest.json", manifest)

    return storage_manager.get_job()
