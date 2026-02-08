"""Base interface for impact models."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List

import pandas as pd


@dataclass
class ModelResult:
    """Standardized model result container.

    All models return this structure, allowing the manager to handle
    storage uniformly while models remain storage-agnostic.

    Attributes:
        model_type: Identifier for the model that produced this result.
        data: Primary result data (serialized to JSON by the manager).
        metadata: Optional metadata about the model run.
        artifacts: Supplementary DataFrames to persist (e.g., per-product details).
            Keys are format-agnostic names; the manager appends the file extension.
    """

    model_type: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, pd.DataFrame] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {"model_type": self.model_type, **self.data, "metadata": self.metadata}


class ModelInterface(ABC):
    """Abstract base class for impact models.

    Defines the unified interface that all impact models must implement.
    This ensures consistent behavior across different modeling approaches
    (interrupted time series, causal inference, metrics approximation, etc.).

    Required methods (must override):
        - connect: Initialize model with configuration
        - fit: Fit model to data
        - validate_params: Validate model-specific parameters before fitting

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
                     dependent_variable).

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

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> None:
        """Validate model-specific parameters before fitting.

        This method is called by ModelsManager before fit() to perform
        early validation of required parameters. All model implementations
        MUST override this method to validate their specific parameters.

        Centralized config validation (process_config) handles known models,
        but this method ensures custom/user-defined models also validate.

        Args:
            params: Dictionary containing parameters that will be passed to fit().
                Typical keys: intervention_date, dependent_variable.

        Raises:
            ValueError: If required parameters are missing or invalid.
        """
        pass

    def get_fit_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Filter parameters to only those accepted by this adapter's fit().

        Called by ModelsManager before fit() to prevent cross-model param pollution.
        Default returns all params (backward compatible). Built-in adapters override.

        Args:
            params: Full params dict (config PARAMS merged with caller overrides).

        Returns:
            Filtered dict for fit().
        """
        return dict(params)

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
