"""
Models Manager for coordinating model operations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import pandas as pd

from .base import ModelInterface, ModelResult


@dataclass
class FitOutput:
    """Structured output from fit_model().

    Provides programmatic access to the results path and all artifact paths,
    so callers do not need to reconstruct file paths from model internals.

    Attributes:
        results_path: Full path/URL to impact_results.json.
        artifact_paths: Mapping of artifact name to full path/URL.
        model_type: The model type that produced this output.
    """

    results_path: str
    artifact_paths: Dict[str, str] = field(default_factory=dict)
    model_type: str = ""


class ModelsManager:
    """Central coordinator for model management.

    Uses dependency injection - the model is passed in via constructor,
    making the manager easy to test with mock implementations.

    Note: measurement_config is expected to be pre-validated via process_config().
    """

    def __init__(
        self,
        measurement_config: Dict[str, Any],
        model: ModelInterface,
    ):
        """Initialize the ModelsManager with injected model.

        Args:
            measurement_config: MEASUREMENT configuration block (pre-validated, with defaults merged).
            model: The model implementation to use for fitting.
        """
        self.measurement_config = measurement_config
        self.model = model

        # Connect the injected model with configuration (PARAMS guaranteed to exist)
        model_config = measurement_config["PARAMS"]
        if not self.model.connect(model_config):
            raise ConnectionError("Failed to connect to model")

    def fit_model(
        self,
        data: pd.DataFrame,
        storage=None,
        **overrides,
    ) -> FitOutput:
        """Fit model using configuration parameters.

        All PARAMS from config are forwarded as kwargs to validate_params() and fit().
        Callers can override any config param via ``**overrides``.

        Args:
            data: DataFrame containing data for model fitting.
            storage: Storage backend for artifacts.
            **overrides: Override any MEASUREMENT.PARAMS value (e.g., intervention_date,
                dependent_variable).

        Returns:
            FitOutput with paths to all persisted files.
        """
        params = dict(self.measurement_config["PARAMS"])

        # Apply caller overrides on top of config values
        params.update({k: v for k, v in overrides.items() if v is not None})

        # Delegate parameter validation to the model
        self.model.validate_params(params)

        # Storage backend is required
        if not storage:
            raise ValueError("Storage backend is required but not provided")

        # Filter params to only those accepted by this adapter
        fit_params = self.model.get_fit_params(params)

        # Fit model - all models return ModelResult (storage-agnostic)
        result: ModelResult = self.model.fit(
            data=data,
            **fit_params,
        )

        # Populate metadata at the manager level (R5)
        result.metadata = {
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }

        # Persist artifacts to storage (centralized here, not in models)
        # Prefix artifact filenames with model_type for namespace hygiene (R2)
        artifact_paths = {}
        for name, df in result.artifacts.items():
            if not isinstance(df, pd.DataFrame):
                raise TypeError(f"Artifact '{name}' must be a DataFrame, got {type(df).__name__}")
            filename = f"{result.model_type}__{name}.parquet"
            storage.write_parquet(filename, df)
            artifact_paths[name] = storage.full_path(filename)

        storage.write_json("impact_results.json", result.to_dict())
        results_path = storage.full_path("impact_results.json")

        return FitOutput(
            results_path=results_path,
            artifact_paths=artifact_paths,
            model_type=result.model_type,
        )

    def get_current_config(self) -> Optional[Dict[str, Any]]:
        """Get the currently loaded configuration."""
        return self.measurement_config
