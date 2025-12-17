"""Base interface for impact models."""

from abc import ABC, abstractmethod
from typing import List
import pandas as pd


class Model(ABC):
    """Abstract base class for impact models.
    
    Defines the unified interface that all impact models must implement.
    This ensures consistent behavior across different modeling approaches
    (interrupted time series, causal inference, regression discontinuity, etc.).
    """

    @abstractmethod
    def fit(
        self,
        data: pd.DataFrame,
        intervention_date: str,
        output_path: str,
        **kwargs
    ) -> str:
        """Fit the model to the provided data and save results.
        
        Args:
            data: DataFrame containing time series data with required columns.
                  Must include 'date' column and dependent variable column.
            intervention_date: Date string (YYYY-MM-DD format) indicating when
                             the intervention occurred.
            output_path: Directory path where model results should be saved.
            **kwargs: Additional model-specific parameters.
        
        Returns:
            str: Path to the saved results file.
        
        Raises:
            ValueError: If data validation fails or required columns are missing.
            RuntimeError: If model fitting fails.
        """
        pass

    @abstractmethod
    def validate_data(self, data: pd.DataFrame) -> bool:
        """Validate that the input data meets model requirements.
        
        Args:
            data: DataFrame to validate.
        
        Returns:
            bool: True if data is valid, False otherwise.
        """
        pass

    @abstractmethod
    def get_required_columns(self) -> List[str]:
        """Get the list of required columns for this model.
        
        Returns:
            List[str]: Column names that must be present in input data.
        """
        pass
