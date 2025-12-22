"""
Models Manager for coordinating model operations.
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from .adapter_interrupted_time_series import InterruptedTimeSeriesAdapter
from .base import Model


class ModelsManager:
    """Central coordinator for model management."""

    def __init__(self, measurement_config: Optional[Dict[str, Any]] = None):
        """Initialize the ModelsManager with MEASUREMENT configuration block."""
        self.model_registry: Dict[str, type] = {}
        self.measurement_config = measurement_config or {
            "MODEL": "interrupted_time_series",
            "PARAMS": {},
        }

        # Register built-in models
        self._register_builtin_models()

        # Validate the measurement config if provided
        if measurement_config is not None:
            self._validate_measurement_config(measurement_config)

    @classmethod
    def from_config_file(cls, config_path: str) -> "ModelsManager":
        """Create ModelsManager from config file, extracting MEASUREMENT block."""
        from ..config import ConfigurationParser

        config_parser = ConfigurationParser()
        full_config = config_parser.parse_config(config_path)
        return cls(full_config["MEASUREMENT"])

    def _register_builtin_models(self) -> None:
        """Register built-in model implementations."""
        self.register_model("interrupted_time_series", InterruptedTimeSeriesAdapter)

    def _validate_measurement_config(self, measurement_config: Dict[str, Any]) -> None:
        """Validate MEASUREMENT configuration block."""
        if "MODEL" not in measurement_config:
            raise ValueError("Missing required field 'MODEL' in MEASUREMENT configuration")

        if "PARAMS" not in measurement_config:
            raise ValueError("Missing required field 'PARAMS' in MEASUREMENT configuration")

    def register_model(self, model_type: str, model_class: type) -> None:
        """Register a new model implementation."""
        if not issubclass(model_class, Model):
            raise ValueError(f"Model class {model_class.__name__} must implement Model")
        self.model_registry[model_type] = model_class

    def get_model(self, model_type: Optional[str] = None) -> Model:
        """Get model implementation based on configuration or specified type."""
        if model_type is None:
            model_type = self.measurement_config["MODEL"]

        if model_type not in self.model_registry:
            raise ValueError(
                f"Unknown model type '{model_type}'. Available: {list(self.model_registry.keys())}"
            )

        model = self.model_registry[model_type]()

        # Connect model with configuration
        model_config = self.measurement_config.get("PARAMS", {})
        if not model.connect(model_config):
            raise ConnectionError(f"Failed to connect to {model_type} model")

        return model

    def fit_model(
        self,
        data: pd.DataFrame,
        intervention_date: Optional[str] = None,
        output_path: str = ".",
        dependent_variable: Optional[str] = None,
        model_type: Optional[str] = None,
        storage=None,
    ) -> str:
        """Fit model using configuration parameters."""
        # Get parameters from config if not provided
        params = self.measurement_config["PARAMS"]

        if intervention_date is None:
            intervention_date = params.get("INTERVENTION_DATE")

        if dependent_variable is None:
            dependent_variable = params.get("DEPENDENT_VARIABLE", "revenue")

        if not intervention_date:
            raise ValueError(
                "INTERVENTION_DATE must be specified in MEASUREMENT.PARAMS configuration"
            )

        # Get model
        model = self.get_model(model_type)

        # Storage backend is required
        if not storage:
            raise ValueError("Storage backend is required but not provided")

        # Set storage on model
        model.storage = storage

        # Fit model
        return model.fit(
            data=data,
            intervention_date=intervention_date,
            output_path=output_path,
            dependent_variable=dependent_variable,
        )

    def get_available_models(self) -> List[str]:
        """Get list of available model types."""
        return list(self.model_registry.keys())
