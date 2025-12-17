"""Interrupted Time Series Model Adapter - adapts SARIMAX to Model interface."""

import pandas as pd
import numpy as np
import json
import logging
from pathlib import Path
from typing import List
from datetime import datetime

from statsmodels.tsa.statespace.sarimax import SARIMAX

from .base import Model


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
        self.model = None
        self.results = None
        self.intervention_date = None
        self.dependent_variable = None
    
    def fit(
        self,
        data: pd.DataFrame,
        intervention_date: str,
        output_path: str,
        dependent_variable: str = "revenue",
        **kwargs
    ) -> str:
        """
        Fit the interrupted time series model and save results.
        
        Args:
            data: DataFrame containing time series data with 'date' column
                  and dependent variable column.
            intervention_date: Date string (YYYY-MM-DD format) indicating when
                             the intervention occurred.
            output_path: Directory path where model results should be saved.
            dependent_variable: Name of the column to model (default: "revenue").
            **kwargs: Additional parameters (e.g., order, seasonal_order for SARIMAX).
        
        Returns:
            str: Path to the saved results file.
        
        Raises:
            ValueError: If data validation fails or required columns are missing.
            RuntimeError: If model fitting fails.
        """
        try:
            # Validate input data
            if not self.validate_data(data):
                raise ValueError(
                    f"Data validation failed. Required columns: {self.get_required_columns()}"
                )
            
            # Check if dependent variable exists
            if dependent_variable not in data.columns:
                raise ValueError(
                    f"Dependent variable '{dependent_variable}' not found in data. "
                    f"Available columns: {list(data.columns)}"
                )
            
            self.dependent_variable = dependent_variable
            self.intervention_date = intervention_date
            
            # Prepare data
            df = data.copy()
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            # Create intervention dummy variable
            intervention_dt = pd.to_datetime(intervention_date)
            df['intervention'] = (df['date'] >= intervention_dt).astype(int)
            
            # Extract time series
            y = df[dependent_variable].values
            
            # Fit SARIMAX model
            # Using simple ARIMA(1,0,0) order by default
            order = kwargs.get('order', (1, 0, 0))
            seasonal_order = kwargs.get('seasonal_order', (0, 0, 0, 0))
            
            self.logger.info(
                f"Fitting SARIMAX model with order={order}, "
                f"seasonal_order={seasonal_order}"
            )
            
            # Fit model with intervention as exogenous variable
            self.model = SARIMAX(
                y,
                exog=df[['intervention']],
                order=order,
                seasonal_order=seasonal_order,
                enforce_stationarity=False,
                enforce_invertibility=False
            )
            
            self.results = self.model.fit(disp=False)
            
            # Calculate impact estimates
            impact_estimates = self._calculate_impact_estimates(df, y)
            
            # Prepare output
            output_data = {
                "model_type": "interrupted_time_series",
                "intervention_date": intervention_date,
                "dependent_variable": dependent_variable,
                "impact_estimates": impact_estimates,
                "model_summary": {
                    "n_observations": int(len(df)),
                    "pre_period_length": int((df['intervention'] == 0).sum()),
                    "post_period_length": int((df['intervention'] == 1).sum()),
                    "aic": float(self.results.aic),
                    "bic": float(self.results.bic)
                }
            }
            
            # Save results to file
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            result_file = output_dir / "impact_results.json"
            with open(result_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            self.logger.info(f"Model results saved to {result_file}")
            
            return str(result_file)
            
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
            pd.to_datetime(data['date'])
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
        return ['date']
    
    def _calculate_impact_estimates(self, df: pd.DataFrame, y: np.ndarray) -> dict:
        """
        Calculate impact estimates from the fitted model.
        
        Args:
            df: DataFrame with intervention indicator.
            y: Original time series values.
        
        Returns:
            dict: Dictionary containing impact estimates.
        """
        # Get pre and post period data
        pre_mask = df['intervention'] == 0
        post_mask = df['intervention'] == 1
        
        pre_values = y[pre_mask]
        post_values = y[post_mask]
        
        pre_mean = float(np.mean(pre_values)) if len(pre_values) > 0 else 0.0
        post_mean = float(np.mean(post_values)) if len(post_values) > 0 else 0.0
        
        # Intervention effect is the difference in means
        intervention_effect = post_mean - pre_mean
        
        # Get coefficient for intervention from model
        try:
            intervention_coef = float(self.results.params.get('intervention', intervention_effect))
        except:
            intervention_coef = intervention_effect
        
        return {
            "intervention_effect": intervention_coef,
            "pre_intervention_mean": pre_mean,
            "post_intervention_mean": post_mean,
            "absolute_change": intervention_effect,
            "percent_change": (intervention_effect / pre_mean * 100) if pre_mean != 0 else 0.0
        }
