"""Load and access job results produced by evaluate_impact()."""

from dataclasses import dataclass
from typing import Any, Dict

import pandas as pd
from artifact_store import JobInfo

# Fixed pipeline files that every run produces.
_PIPELINE_KEYS = frozenset(
    {
        "config",
        "products",
        "business_metrics",
        "transformed_metrics",
        "impact_results",
    }
)

_FORMAT_READERS = {
    "json": lambda store, path: store.read_json(path),
    "yaml": lambda store, path: store.read_yaml(path),
    "parquet": lambda store, path: store.read_parquet(path),
}


@dataclass
class MeasureJobResult:
    """Typed container for all artifacts produced by a single pipeline run.

    Attributes:
        job_id: Unique identifier for the job.
        model_type: Model identifier (e.g. ``"interrupted_time_series"``).
        created_at: ISO-8601 timestamp of job creation.
        config: The YAML configuration used for this run.
        impact_results: The ``impact_results.json`` envelope (model_type, data, metadata).
        products: Product catalog DataFrame.
        business_metrics: Raw business metrics DataFrame.
        transformed_metrics: Transformed metrics DataFrame.
        model_artifacts: Model-specific supplementary DataFrames, keyed by
            artifact name with the ``{model_type}__`` prefix stripped.
    """

    job_id: str
    model_type: str
    created_at: str
    config: Dict[str, Any]
    impact_results: Dict[str, Any]
    products: pd.DataFrame
    business_metrics: pd.DataFrame
    transformed_metrics: pd.DataFrame
    model_artifacts: Dict[str, pd.DataFrame]


def load_results(job_info: JobInfo) -> MeasureJobResult:
    """Load all artifacts from a completed pipeline run.

    Reads ``manifest.json`` to discover files, then loads each one using the
    format-appropriate reader.  Model-specific artifacts (those not in the
    fixed pipeline set) are collected into ``model_artifacts`` with the
    ``{model_type}__`` prefix stripped from their keys.

    Args:
        job_info: ``JobInfo`` returned by :func:`evaluate_impact`.

    Returns:
        MeasureJobResult: Typed container with every artifact.

    Raises:
        FileNotFoundError: If the job directory or manifest is missing.
        ValueError: If the manifest's major schema version is incompatible.
    """
    store = job_info.get_store()

    if not store.exists("manifest.json"):
        raise FileNotFoundError(f"manifest.json not found in job directory: {store.full_path('manifest.json')}")

    manifest = store.read_json("manifest.json")

    files = manifest["files"]
    model_type = manifest["model_type"]

    # Load fixed pipeline artifacts.
    config = _load_file(store, files["config"])
    impact_results = _load_file(store, files["impact_results"])
    products = _load_file(store, files["products"])
    business_metrics = _load_file(store, files["business_metrics"])
    transformed_metrics = _load_file(store, files["transformed_metrics"])

    # Collect model-specific artifacts (everything not in the fixed set).
    model_artifacts: Dict[str, pd.DataFrame] = {}
    prefix = f"{model_type}__"
    for key, file_info in files.items():
        if key not in _PIPELINE_KEYS:
            name = key[len(prefix) :] if key.startswith(prefix) else key
            model_artifacts[name] = _load_file(store, file_info)

    return MeasureJobResult(
        job_id=job_info.job_id,
        model_type=model_type,
        created_at=manifest["created_at"],
        config=config,
        impact_results=impact_results,
        products=products,
        business_metrics=business_metrics,
        transformed_metrics=transformed_metrics,
        model_artifacts=model_artifacts,
    )


def _load_file(store, file_info: Dict[str, str]) -> Any:
    """Load a single file using the format declared in the manifest."""
    fmt = file_info["format"]
    path = file_info["path"]
    reader = _FORMAT_READERS.get(fmt)
    if reader is None:
        raise ValueError(f"Unsupported format '{fmt}' for file '{path}'")
    return reader(store, path)
