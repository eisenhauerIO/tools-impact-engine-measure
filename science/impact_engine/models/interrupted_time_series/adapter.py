"""Interrupted Time Series Model Adapter - adapts SARIMAX to Model interface."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

from ..base import Model


@dataclass
class TransformedInput:
    """Container for transformed model input data.

    This dataclass eliminates hidden state by explicitly passing
    all necessary data between transformation and result formatting.
    """

    y: np.ndarray
    exog: pd.DataFrame
    data: pd.DataFrame
    dependent_variable: str
    intervention_date: str
    order: Tuple[int, int, int]
    seasonal_order: Tuple[int, int, int, int]


class InterruptedTimeSeriesAdapter(Model):
    """
    Adapter for Interrupted Time Series (ITS) model that implements Model interface.

    This adapter uses SARIMAX from statsmodels to fit a time series model
    with an intervention dummy variable to estimate the causal impact
    of an intervention on a business metric.

    The model assumes:
    - Data is ordered chronologically
    - Intervention occurs at a specific point in time
    - Pre and post-intervention periods have sufficient observations
    """

    def __init__(self):
        """Initialize the InterruptedTimeSeriesAdapter."""
        self.logger = logging.getLogger(__name__)
        self.is_connected = False
        self.config = None
        self.storage = None

    def connect(self, config: Dict[str, Any]) -> bool:
        """Initialize model with configuration parameters."""
        # Validate order parameter
        order = config.get("order", (1, 0, 0))
        if not isinstance(order, tuple) or len(order) != 3:
            raise ValueError("Order must be a tuple of 3 integers (p, d, q)")

        # Validate seasonal_order parameter
        seasonal_order = config.get("seasonal_order", (0, 0, 0, 0))
        if not isinstance(seasonal_order, tuple) or len(seasonal_order) != 4:
            raise ValueError("Seasonal order must be a tuple of 4 integers (P, D, Q, s)")

        # Validate dependent_variable
        dependent_variable = config.get("dependent_variable", "revenue")
        if not isinstance(dependent_variable, str):
            raise ValueError("Dependent variable must be a string")

        self.config = {
            "order": order,
            "seasonal_order": seasonal_order,
            "dependent_variable": dependent_variable,
        }
        self.is_connected = True
        return True

    def validate_connection(self) -> bool:
        """Validate that the model is properly initialized and ready to use."""
        if not self.is_connected:
            return False

        try:
            # Check if statsmodels is available
            from statsmodels.tsa.statespace.sarimax import SARIMAX  # noqa: F401

            return True
        except ImportError:
            return False

    def validate_params(self, **kwargs) -> None:
        """Validate that required parameters are provided for ITS model.

        ITS model requires intervention_date to determine the treatment point.

        Args:
            **kwargs: Parameters that will be passed to fit().

        Raises:
            ValueError: If intervention_date is missing.
        """
        intervention_date = kwargs.get("intervention_date")
        if not intervention_date:
            raise ValueError(
                "intervention_date must be specified in MEASUREMENT.PARAMS configuration "
                "for interrupted_time_series model"
            )

    def fit(self, data: pd.DataFrame, **kwargs) -> str:
        """
        Fit the interrupted time series model and save results.

        Args:
            data: DataFrame containing time series data with 'date' column
                  and dependent variable column.
            **kwargs: Model parameters:
                - intervention_date (str): Date (YYYY-MM-DD) when intervention occurred. Required.
                - output_path (str): Directory path for saving results. Required.
                - dependent_variable (str): Column to model (default: "revenue").
                - order (tuple): SARIMAX order (p, d, q).
                - seasonal_order (tuple): SARIMAX seasonal order (P, D, Q, s).

        Returns:
            str: Path to the saved results file.

        Raises:
            ValueError: If data validation fails or required columns are missing.
            RuntimeError: If model fitting fails.
        """
        # Extract required kwargs
        intervention_date = kwargs.get("intervention_date")
        output_path = kwargs.get("output_path")
        dependent_variable = kwargs.get("dependent_variable", "revenue")

        if not intervention_date:
            raise ValueError("intervention_date is required for InterruptedTimeSeriesAdapter")
        if not output_path:
            raise ValueError("output_path is required for InterruptedTimeSeriesAdapter")

        if not self.is_connected:
            raise ConnectionError("Model not connected. Call connect() first.")

        try:
            # Validate input data
            if not self.validate_data(data):
                raise ValueError(
                    f"Data validation failed. Required columns: {self.get_required_columns()}"
                )

            # Prepare model input (stateless transformation)
            # Remove extracted params from kwargs to avoid duplicate arguments
            model_kwargs = {
                k: v for k, v in kwargs.items()
                if k not in ("intervention_date", "output_path", "dependent_variable")
            }
            transformed = self._prepare_model_input(
                data, intervention_date, dependent_variable, **model_kwargs
            )

            # Fit SARIMAX model
            self.logger.info(
                f"Fitting SARIMAX model with order={transformed.order}, "
                f"seasonal_order={transformed.seasonal_order}"
            )

            model = SARIMAX(
                transformed.y,
                exog=transformed.exog,
                order=transformed.order,
                seasonal_order=transformed.seasonal_order,
                enforce_stationarity=False,
                enforce_invertibility=False,
            )

            results = model.fit(disp=False)

            # Format results (explicitly pass transformed data)
            standardized_results = self._format_results(results, transformed)

            # Save results using storage backend
            if not self.storage:
                raise ValueError("Storage backend is required but not configured")

            result_path = f"{output_path}/impact_results.json"
            self.storage.write_json(result_path, standardized_results)
            stored_path = self.storage.full_path(result_path)
            self.logger.info(f"Model results saved to {stored_path}")
            return stored_path

        except Exception as e:
            self.logger.error(f"Error fitting InterruptedTimeSeriesAdapter: {e}")
            raise RuntimeError(f"Model fitting failed: {e}") from e

    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        Validate that the input data meets model requirements.

        Args:
            data: DataFrame to validate.

        Returns:
            bool: True if data is valid, False otherwise.
        """
        if data.empty:
            self.logger.warning("Data is empty")
            return False

        required_cols = self.get_required_columns()
        missing_cols = [col for col in required_cols if col not in data.columns]

        if missing_cols:
            self.logger.warning(f"Missing required columns: {missing_cols}")
            return False

        # Check that date column can be converted to datetime
        try:
            pd.to_datetime(data["date"])
        except Exception as e:
            self.logger.warning(f"Cannot convert 'date' column to datetime: {e}")
            return False

        # Check that we have at least some observations
        if len(data) < 3:
            self.logger.warning("Data must have at least 3 observations")
            return False

        return True

    def get_required_columns(self) -> List[str]:
        """
        Get the list of required columns for this model.

        Returns:
            List[str]: Column names that must be present in input data.
        """
        return ["date"]

    def _prepare_model_input(
        self,
        data: pd.DataFrame,
        intervention_date: str,
        dependent_variable: str,
        **kwargs,
    ) -> TransformedInput:
        """Prepare data for SARIMAX model fitting.

        This method transforms raw input data into the format required by SARIMAX,
        returning all necessary data in a TransformedInput container.

        Args:
            data: Raw input DataFrame with date and metric columns.
            intervention_date: Date string (YYYY-MM-DD) for intervention.
            dependent_variable: Name of the column to model.
            **kwargs: Optional overrides for order and seasonal_order.

        Returns:
            TransformedInput: Container with all data needed for model fitting.

        Raises:
            ValueError: If dependent variable is not in data.
        """
        # Check if dependent variable exists
        if dependent_variable not in data.columns:
            raise ValueError(
                f"Dependent variable '{dependent_variable}' not found in data. "
                f"Available columns: {list(data.columns)}"
            )

        # Prepare data
        df = data.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        # Create intervention dummy variable
        intervention_dt = pd.to_datetime(intervention_date)
        df["intervention"] = (df["date"] >= intervention_dt).astype(int)

        # Extract time series and exogenous variables
        y = df[dependent_variable].values
        exog = df[["intervention"]]

        # Get model parameters from config or kwargs
        order = kwargs.get("order", self.config.get("order", (1, 0, 0)))
        seasonal_order = kwargs.get(
            "seasonal_order", self.config.get("seasonal_order", (0, 0, 0, 0))
        )

        return TransformedInput(
            y=y,
            exog=exog,
            data=df,
            dependent_variable=dependent_variable,
            intervention_date=intervention_date,
            order=order,
            seasonal_order=seasonal_order,
        )

    def _format_results(self, model_results: Any, transformed: TransformedInput) -> Dict[str, Any]:
        """Format SARIMAX results into standardized impact engine format.

        Args:
            model_results: Fitted SARIMAX results object.
            transformed: The TransformedInput used for fitting.

        Returns:
            Dict containing standardized impact analysis results.

        Raises:
            ValueError: If model_results lacks expected attributes.
        """
        if not hasattr(model_results, "params"):
            raise ValueError("Expected SARIMAX results object with params attribute")

        # Calculate impact estimates
        impact_estimates = self._calculate_impact_estimates(
            transformed.data, transformed.y, model_results
        )

        # Prepare standardized output
        df = transformed.data
        return {
            "model_type": "interrupted_time_series",
            "intervention_date": transformed.intervention_date,
            "dependent_variable": transformed.dependent_variable,
            "impact_estimates": impact_estimates,
            "model_summary": {
                "n_observations": int(len(df)),
                "pre_period_length": int((df["intervention"] == 0).sum()),
                "post_period_length": int((df["intervention"] == 1).sum()),
                "aic": float(model_results.aic),
                "bic": float(model_results.bic),
            },
        }

    def _calculate_impact_estimates(
        self, df: pd.DataFrame, y: np.ndarray, model_results: Any
    ) -> dict:
        """
        Calculate impact estimates from the fitted model.

        Args:
            df: DataFrame with intervention indicator.
            y: Original time series values.
            model_results: Fitted SARIMAX results object.

        Returns:
            dict: Dictionary containing impact estimates.
        """
        # Get pre and post period data
        pre_mask = df["intervention"] == 0
        post_mask = df["intervention"] == 1

        pre_values = y[pre_mask]
        post_values = y[post_mask]

        pre_mean = float(np.mean(pre_values)) if len(pre_values) > 0 else 0.0
        post_mean = float(np.mean(post_values)) if len(post_values) > 0 else 0.0

        # Intervention effect is the difference in means
        intervention_effect = post_mean - pre_mean

        # Get coefficient for intervention from model
        try:
            intervention_coef = float(model_results.params.get("intervention", intervention_effect))
        except (KeyError, AttributeError, TypeError):
            intervention_coef = intervention_effect

        return {
            "intervention_effect": intervention_coef,
            "pre_intervention_mean": pre_mean,
            "post_intervention_mean": post_mean,
            "absolute_change": intervention_effect,
            "percent_change": (intervention_effect / pre_mean * 100) if pre_mean != 0 else 0.0,
        }

    def transform_outbound(
        self, data: pd.DataFrame, intervention_date: str, **kwargs
    ) -> Dict[str, Any]:
        """Transform impact engine format to SARIMAX model format.

        Note: This method is kept for interface compliance but internally
        uses _prepare_model_input for the actual transformation.
        """
        dependent_variable = kwargs.get(
            "dependent_variable", self.config.get("dependent_variable", "revenue")
        )
        transformed = self._prepare_model_input(
            data, intervention_date, dependent_variable, **kwargs
        )
        return {
            "y": transformed.y,
            "exog": transformed.exog,
            "order": transformed.order,
            "seasonal_order": transformed.seasonal_order,
            "data": transformed.data,
            "dependent_variable": transformed.dependent_variable,
            "intervention_date": transformed.intervention_date,
        }

    def transform_inbound(self, model_results: Any) -> Dict[str, Any]:
        """Transform SARIMAX results to impact engine format.

        Note: This method requires transform_outbound to have been called first
        to set up necessary state. For stateless operation, use _format_results
        directly with a TransformedInput object.
        """
        raise NotImplementedError(
            "transform_inbound requires prior state. Use _format_results with "
            "TransformedInput instead for stateless operation."
        )
