"""
Models Manager for coordinating model operations.
"""

from typing import Any, Dict, Optional

import pandas as pd

from .base import ModelInterface, ModelResult


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
    ) -> str:
        """Fit model using configuration parameters.

        All PARAMS from config are forwarded as kwargs to validate_params() and fit().
        Callers can override any config param via **overrides.

        Args:
            data: DataFrame containing data for model fitting.
            storage: Storage backend for artifacts.
            **overrides: Override any MEASUREMENT.PARAMS value (e.g., intervention_date,
                dependent_variable).

        Returns:
            Path to output artifacts.
        """
        params = dict(self.measurement_config["PARAMS"])

        # Apply caller overrides on top of config values
        params.update({k: v for k, v in overrides.items() if v is not None})

        # Delegate parameter validation to the model
        self.model.validate_params(params)

        # Storage backend is required
        if not storage:
            raise ValueError("Storage backend is required but not provided")

        # Fit model - all models return ModelResult (storage-agnostic)
        result: ModelResult = self.model.fit(
            data=data,
            storage=storage,
            **params,
        )

        # Persist to storage (centralized here, not in models)
        storage.write_json("impact_results.json", result.to_dict())
        return storage.full_path("impact_results.json")

    def get_current_config(self) -> Optional[Dict[str, Any]]:
        """Get the currently loaded configuration."""
        return self.measurement_config
