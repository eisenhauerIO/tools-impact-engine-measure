"""Experiment Model Adapter - thin wrapper around statsmodels OLS with R-style formulas."""

import logging
from typing import Any, Dict, List

import pandas as pd
import statsmodels.formula.api as smf

from ..base import ModelInterface, ModelResult
from ..factory import MODEL_REGISTRY


@MODEL_REGISTRY.register_decorator("experiment")
class ExperimentAdapter(ModelInterface):
    """Estimates treatment effects via OLS regression with R-style formulas.

    Constraints:
    - formula parameter required in MEASUREMENT.PARAMS
    - DataFrame must contain all variables referenced in the formula
    """

    def __init__(self):
        """Initialize the ExperimentAdapter."""
        self.logger = logging.getLogger(__name__)
        self.is_connected = False
        self.config = None

    def connect(self, config: Dict[str, Any]) -> bool:
        """Initialize model with configuration parameters.

        Config is pre-validated with defaults merged via process_config().
        """
        formula = config.get("formula")
        if not formula or not isinstance(formula, str):
            raise ValueError(
                "formula is required and must be a string (e.g., 'y ~ treatment + x1'). "
                "Specify in MEASUREMENT.PARAMS configuration."
            )

        self.config = {"formula": formula}
        self.is_connected = True
        return True

    def validate_connection(self) -> bool:
        """Validate that the model is properly initialized and ready to use."""
        if not self.is_connected:
            return False

        try:
            import statsmodels.formula.api  # noqa: F401

            return True
        except ImportError:
            return False

    def validate_params(self, params: Dict[str, Any]) -> None:
        """Validate experiment-specific parameters.

        Args:
            params: Parameters dict with formula, etc.

        Raises:
            ValueError: If formula is missing.
        """
        formula = params.get("formula")
        if not formula or not isinstance(formula, str):
            raise ValueError(
                "formula is required for ExperimentAdapter. "
                "Specify in MEASUREMENT.PARAMS configuration."
            )

    _CONFIG_PARAMS = frozenset(
        {
            "dependent_variable",
            "intervention_date",
            "order",
            "seasonal_order",
            "n_strata",
            "estimand",
            "treatment_column",
            "covariate_columns",
            "formula",
            "metric_before_column",
            "metric_after_column",
            "baseline_column",
            "RESPONSE",
            # Nearest neighbour matching params
            "caliper",
            "replace",
            "ratio",
            "shuffle",
            "random_state",
            "n_jobs",
        }
    )

    def get_fit_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Exclude known config keys, pass library kwargs through to statsmodels."""
        return {k: v for k, v in params.items() if k not in self._CONFIG_PARAMS}

    def fit(self, data: pd.DataFrame, **kwargs) -> ModelResult:
        """Fit OLS model using statsmodels formula API and return results.

        Args:
            data: DataFrame containing all variables referenced in the formula.
            **kwargs: Passed through to statsmodels OLS .fit()
                (e.g., cov_type='HC3' for robust standard errors).

        Returns:
            ModelResult: Standardized result container.

        Raises:
            ConnectionError: If model not connected.
            RuntimeError: If model fitting fails.
        """
        if not self.is_connected:
            raise ConnectionError("Model not connected. Call connect() first.")

        if not self.validate_data(data):
            raise ValueError("Data validation failed. DataFrame must not be empty.")

        formula = self.config["formula"]

        try:
            model = smf.ols(formula, data=data)
            results = model.fit(**kwargs)

            # Extract confidence intervals as a nested dict
            conf_int_df = results.conf_int()
            conf_int = {
                var: [float(conf_int_df.loc[var, 0]), float(conf_int_df.loc[var, 1])]
                for var in conf_int_df.index
            }

            impact_estimates = {
                "params": {k: float(v) for k, v in results.params.items()},
                "bse": {k: float(v) for k, v in results.bse.items()},
                "tvalues": {k: float(v) for k, v in results.tvalues.items()},
                "pvalues": {k: float(v) for k, v in results.pvalues.items()},
                "conf_int": conf_int,
            }

            model_summary = {
                "rsquared": float(results.rsquared),
                "rsquared_adj": float(results.rsquared_adj),
                "fvalue": float(results.fvalue),
                "f_pvalue": float(results.f_pvalue),
                "nobs": int(results.nobs),
                "df_resid": float(results.df_resid),
            }

            self.logger.info(
                f"Experiment model fit complete: formula='{formula}', "
                f"nobs={int(results.nobs)}, R²={results.rsquared:.4f}"
            )

            return ModelResult(
                model_type="experiment",
                data={
                    "model_params": {"formula": formula},
                    "impact_estimates": impact_estimates,
                    "model_summary": model_summary,
                },
            )

        except Exception as e:
            self.logger.error(f"Error fitting ExperimentAdapter: {e}")
            raise RuntimeError(f"Model fitting failed: {e}") from e

    def get_required_columns(self) -> List[str]:
        """Get required column names.

        Returns empty list; statsmodels validates formula variables against
        the DataFrame natively.
        """
        return []
