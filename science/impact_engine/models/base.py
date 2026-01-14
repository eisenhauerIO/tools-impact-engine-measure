"""Base interface for impact models."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

import pandas as pd


class Model(ABC):
    """Abstract base class for impact models.

    Defines the unified interface that all impact models must implement.
    This ensures consistent behavior across different modeling approaches
    (interrupted time series, causal inference, metrics approximation, etc.).

    Required methods (must override):
        - connect: Initialize model with configuration
        - fit: Fit model to data

    Optional methods (have sensible defaults):
        - validate_connection: Check if model is ready
        - validate_data: Check if input data is valid
        - get_required_columns: Return list of required columns
        - transform_outbound: Transform data to external format
        - transform_inbound: Transform results from external format
    """

    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> bool:
        """Initialize model with configuration parameters.

        Args:
            config: Dictionary containing model configuration parameters

        Returns:
            bool: True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    def fit(self, data: pd.DataFrame, **kwargs) -> Any:
        """Fit the model to the provided data.

        Args:
            data: DataFrame containing data for model fitting.
            **kwargs: Model-specific parameters (e.g., intervention_date,
                     output_path, dependent_variable).

        Returns:
            Model-specific results (Dict, str path, etc.)

        Raises:
            ValueError: If data validation fails or required columns are missing.
            RuntimeError: If model fitting fails.
        """
        pass

    def validate_connection(self) -> bool:
        """Validate that the model is properly initialized and ready to use.

        Default implementation returns True. Override for custom validation.

        Returns:
            bool: True if model is ready, False otherwise.
        """
        return True

    def validate_data(self, data: pd.DataFrame) -> bool:
        """Validate that the input data meets model requirements.

        Default implementation checks if data is non-empty.
        Override for custom validation.

        Args:
            data: DataFrame to validate.

        Returns:
            bool: True if data is valid, False otherwise.
        """
        return data is not None and not data.empty

    def get_required_columns(self) -> List[str]:
        """Get the list of required columns for this model.

        Default implementation returns empty list.
        Override if model requires specific columns.

        Returns:
            List[str]: Column names that must be present in input data.
        """
        return []

    def validate_params(self, **kwargs) -> None:
        """Validate model-specific parameters before fitting.

        This method allows models to declare and validate their own parameter
        requirements instead of having this logic in the manager. Each model
        should override this to check for required parameters.

        Default implementation does nothing (no required params).
        Override to validate model-specific requirements.

        Args:
            **kwargs: Parameters that will be passed to fit().

        Raises:
            ValueError: If required parameters are missing or invalid.
        """
        pass

    def transform_outbound(self, data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Transform impact engine format to model library format.

        Default implementation is pass-through.
        Override for models that need data transformation.

        Args:
            data: DataFrame with impact engine standardized format
            **kwargs: Additional model-specific parameters

        Returns:
            Dictionary with parameters formatted for the model library
        """
        return {"data": data, **kwargs}

    def transform_inbound(self, model_results: Any) -> Dict[str, Any]:
        """Transform model library results to impact engine format.

        Default implementation returns results as-is (or wrapped in dict).
        Override for models that need result transformation.

        Args:
            model_results: Raw results from the model library

        Returns:
            Dictionary with standardized impact analysis results
        """
        if isinstance(model_results, dict):
            return model_results
        return {"results": model_results}
