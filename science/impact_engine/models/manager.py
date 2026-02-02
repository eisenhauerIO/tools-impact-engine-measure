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
        intervention_date: Optional[str] = None,
        dependent_variable: Optional[str] = None,
        storage=None,
    ) -> str:
        """Fit model using configuration parameters.

        Args:
            data: DataFrame containing data for model fitting.
            intervention_date: Override for intervention date (uses config if None).
            dependent_variable: Override for dependent variable (uses config if None).
            storage: Storage backend for artifacts.

        Returns:
            Path to output artifacts.
        """
        params = self.measurement_config["PARAMS"]

        # Use config values if not overridden by caller
        if intervention_date is None:
            intervention_date = params["intervention_date"]

        if dependent_variable is None:
            dependent_variable = params["dependent_variable"]

        # Delegate parameter validation to the model
        self.model.validate_params(
            {
                "intervention_date": intervention_date,
                "dependent_variable": dependent_variable,
            }
        )

        # Storage backend is required
        if not storage:
            raise ValueError("Storage backend is required but not provided")

        # Fit model - all models return ModelResult (storage-agnostic)
        result: ModelResult = self.model.fit(
            data=data,
            intervention_date=intervention_date,
            dependent_variable=dependent_variable,
            storage=storage,
        )

        # Persist to storage (centralized here, not in models)
        result_dict = result.to_dict()

        # Extract per_product to separate CSV file (can be large)
        if "per_product" in result_dict:
            per_product = result_dict.pop("per_product")
            if per_product:
                per_product_df = pd.DataFrame(per_product)
                storage.write_csv("product_level_impacts.csv", per_product_df)

        storage.write_json("impact_results.json", result_dict)
        return storage.full_path("impact_results.json")

    def get_current_config(self) -> Optional[Dict[str, Any]]:
        """Get the currently loaded configuration."""
        return self.measurement_config
