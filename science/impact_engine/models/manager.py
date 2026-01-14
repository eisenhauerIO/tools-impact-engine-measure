"""
Models Manager for coordinating model operations.
"""

from typing import Any, Dict, Optional

import pandas as pd

from .base import Model


class ModelsManager:
    """Central coordinator for model management.

    Uses dependency injection - the model is passed in via constructor,
    making the manager easy to test with mock implementations.
    """

    def __init__(
        self,
        measurement_config: Dict[str, Any],
        model: Model,
    ):
        """Initialize the ModelsManager with injected model.

        Args:
            measurement_config: MEASUREMENT configuration block containing model params.
            model: The model implementation to use for fitting.
        """
        self.measurement_config = measurement_config
        self.model = model

        # Validate the measurement config
        self._validate_measurement_config(measurement_config)

        # Connect the injected model with configuration
        model_config = measurement_config.get("PARAMS", {})
        if not self.model.connect(model_config):
            raise ConnectionError("Failed to connect to model")

    def _validate_measurement_config(self, measurement_config: Dict[str, Any]) -> None:
        """Validate MEASUREMENT configuration block."""
        if "PARAMS" not in measurement_config:
            raise ValueError("Missing required field 'PARAMS' in MEASUREMENT configuration")

    def fit_model(
        self,
        data: pd.DataFrame,
        intervention_date: Optional[str] = None,
        output_path: str = ".",
        dependent_variable: Optional[str] = None,
        storage=None,
    ) -> str:
        """Fit model using configuration parameters."""
        # Get parameters from config if not provided
        params = self.measurement_config["PARAMS"]

        # Support both lowercase and uppercase param names for backward compatibility
        if intervention_date is None:
            intervention_date = params.get("intervention_date") or params.get("INTERVENTION_DATE")

        if dependent_variable is None:
            dependent_variable = (
                params.get("dependent_variable")
                or params.get("DEPENDENT_VARIABLE")
                or "revenue"
            )

        # ITS model requires intervention_date, but metrics_approximation doesn't
        model_type = self.measurement_config.get("MODEL", "")
        if model_type == "interrupted_time_series" and not intervention_date:
            raise ValueError(
                "intervention_date must be specified in MEASUREMENT.PARAMS configuration "
                "for interrupted_time_series model"
            )

        # Storage backend is required
        if not storage:
            raise ValueError("Storage backend is required but not provided")

        # Set storage on model
        self.model.storage = storage

        # Fit model
        return self.model.fit(
            data=data,
            intervention_date=intervention_date,
            output_path=output_path,
            dependent_variable=dependent_variable,
        )

    def get_current_config(self) -> Optional[Dict[str, Any]]:
        """Get the currently loaded configuration."""
        return self.measurement_config
