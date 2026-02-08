"""Synthetic Control Model Adapter - thin wrapper around CausalPy's SyntheticControl."""

import logging
from typing import Any, Dict, List

import pandas as pd

from ..base import ModelInterface, ModelResult
from ..factory import MODEL_REGISTRY
from .transforms import pivot_to_wide


@MODEL_REGISTRY.register_decorator("synthetic_control")
class SyntheticControlAdapter(ModelInterface):
    """Estimates causal impact using the synthetic control method via CausalPy.

    Constraints:
    - Data must be in panel (long) format with unit, time, outcome, and treatment columns
    - treatment_time, treated_unit, and outcome_column required in MEASUREMENT.PARAMS
    - Requires at least one treated unit and one control unit
    """

    def __init__(self):
        """Initialize the SyntheticControlAdapter."""
        self.logger = logging.getLogger(__name__)
        self.is_connected = False
        self.config = None

    def connect(self, config: Dict[str, Any]) -> bool:
        """Initialize model with structural configuration parameters.

        Config is pre-validated with defaults merged via process_config().
        Sampler parameters (n_samples, n_chains, etc.) flow through fit() kwargs.
        """
        unit_column = config.get("unit_column", "unit_id")
        if not isinstance(unit_column, str):
            raise ValueError("unit_column must be a string")

        time_column = config.get("time_column", "date")
        if not isinstance(time_column, str):
            raise ValueError("time_column must be a string")

        outcome_column = config.get("outcome_column")
        if not outcome_column or not isinstance(outcome_column, str):
            raise ValueError(
                "outcome_column is required and must be a string. "
                "Specify in MEASUREMENT.PARAMS configuration."
            )

        self.config = {
            "unit_column": unit_column,
            "time_column": time_column,
            "outcome_column": outcome_column,
        }
        self.is_connected = True
        return True

    def validate_connection(self) -> bool:
        """Validate that the model is properly initialized and ready to use."""
        if not self.is_connected:
            return False

        try:
            import causalpy  # noqa: F401

            return True
        except ImportError:
            return False

    def validate_params(self, params: Dict[str, Any]) -> None:
        """Validate synthetic control-specific parameters.

        Only validates the three truly required params (null in config_defaults.yaml).

        Args:
            params: Parameters dict with treatment_time, treated_unit, etc.

        Raises:
            ValueError: If required parameters are missing.
        """
        if params.get("treatment_time") is None:
            raise ValueError(
                "treatment_time is required for SyntheticControlAdapter. "
                "Specify in MEASUREMENT.PARAMS configuration."
            )
        if not params.get("treated_unit"):
            raise ValueError(
                "treated_unit is required for SyntheticControlAdapter. "
                "Specify in MEASUREMENT.PARAMS configuration."
            )
        if not params.get("outcome_column"):
            raise ValueError(
                "outcome_column is required for SyntheticControlAdapter. "
                "Specify in MEASUREMENT.PARAMS configuration."
            )

    _FIT_PARAMS = frozenset(
        {
            "treatment_time",
            "treated_unit",
            "unit_column",
            "outcome_column",
            "time_column",
            "n_samples",
            "n_chains",
            "target_accept",
            "random_seed",
        }
    )

    def get_fit_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """SC accepts treatment_time, treated_unit, columns, and sampler params."""
        return {k: v for k, v in params.items() if k in self._FIT_PARAMS}

    def fit(self, data: pd.DataFrame, **kwargs) -> ModelResult:
        """Fit the synthetic control model and return results.

        Args:
            data: Panel DataFrame with unit, time, outcome, and treatment columns.
            **kwargs: Model parameters:
                - treatment_time: When the intervention occurred (index value). Required.
                - treated_unit (str): Name of the treated unit. Required.
                - outcome_column (str): Column with the outcome variable. Required.
                - unit_column (str): Column identifying units (default from config).
                - time_column (str): Column identifying time periods (default from config).
                - n_samples (int): Number of posterior samples (default: 2000).
                - n_chains (int): Number of MCMC chains (default: 4).
                - target_accept (float): Target acceptance rate (default: 0.95).
                - random_seed (int): Random seed for reproducibility.

        Returns:
            ModelResult: Standardized result container.

        Raises:
            ConnectionError: If model not connected.
            ValueError: If data validation fails.
            RuntimeError: If model fitting fails.
        """
        if not self.is_connected:
            raise ConnectionError("Model not connected. Call connect() first.")

        if not self.validate_data(data):
            raise ValueError(
                f"Data validation failed. Required columns: {self.get_required_columns()}"
            )

        try:
            import causalpy as cp

            # Read params from kwargs (already filtered by get_fit_params)
            treatment_time = kwargs["treatment_time"]
            treated_unit = str(kwargs["treated_unit"])
            unit_column = kwargs.get("unit_column", self.config["unit_column"])
            time_column = kwargs.get("time_column", self.config["time_column"])
            outcome_column = kwargs.get("outcome_column", self.config["outcome_column"])

            # Sampler params with defaults
            n_samples = kwargs.get("n_samples", 2000)
            n_chains = kwargs.get("n_chains", 4)
            target_accept = kwargs.get("target_accept", 0.95)
            random_seed = kwargs.get("random_seed")

            # Pivot long → wide
            wide_df, treated_units, control_units = pivot_to_wide(
                data,
                unit_column=unit_column,
                time_column=time_column,
                outcome_column=outcome_column,
            )

            # Build sample_kwargs for CausalPy
            sample_kwargs = {
                "draws": n_samples,
                "chains": n_chains,
                "target_accept": target_accept,
            }
            if random_seed is not None:
                sample_kwargs["random_seed"] = random_seed

            self.logger.info(
                f"Fitting SyntheticControl: treated={treated_unit}, "
                f"n_control={len(control_units)}, "
                f"samples={n_samples}, chains={n_chains}"
            )

            # Fit CausalPy model
            result = cp.SyntheticControl(
                wide_df,
                treatment_time,
                control_units=control_units,
                treated_units=[treated_unit],
                model=cp.pymc_models.WeightedSumFitter(
                    sample_kwargs=sample_kwargs,
                ),
            )

            # Extract results via effect_summary() — CausalPy's clean API
            # Returns EffectSummary with .table (DataFrame) having "average" and
            # "cumulative" rows, and columns: mean, median, hdi_lower, hdi_upper,
            # prob_positive, prob_negative, relative_hdi_lower, relative_hdi_upper
            n_pre = int((wide_df.index < treatment_time).sum())
            n_post = int((wide_df.index >= treatment_time).sum())

            effect = result.effect_summary(treated_unit=treated_unit)
            tbl = effect.table

            avg_row = tbl.loc["average"]
            cum_row = tbl.loc["cumulative"]

            # Tail probability: probability effect is negative (no real effect)
            tail_probability = float(avg_row.get("prob_negative", avg_row.get("P(negative)", 0)))

            impact_estimates = {
                "mean_effect": float(avg_row["mean"]),
                "median_effect": float(avg_row["median"]),
                "hdi_lower": float(avg_row["hdi_lower"]),
                "hdi_upper": float(avg_row["hdi_upper"]),
                "cumulative_effect": float(cum_row["mean"]),
                "tail_probability": tail_probability,
            }

            model_summary = {
                "n_pre_periods": n_pre,
                "n_post_periods": n_post,
                "n_control_units": len(control_units),
                "sampler_stats": {
                    "n_samples": n_samples,
                    "n_chains": n_chains,
                    "target_accept": target_accept,
                    "random_seed": random_seed,
                },
            }

            self.logger.info(
                f"SyntheticControl fit complete: "
                f"mean_effect={impact_estimates['mean_effect']:.4f}"
            )

            return ModelResult(
                model_type="synthetic_control",
                data={
                    "model_params": {
                        "treatment_time": treatment_time,
                        "treated_unit": treated_unit,
                    },
                    "impact_estimates": impact_estimates,
                    "model_summary": model_summary,
                },
            )

        except Exception as e:
            self.logger.error(f"Error fitting SyntheticControlAdapter: {e}")
            raise RuntimeError(f"Model fitting failed: {e}") from e

    def validate_data(self, data: pd.DataFrame) -> bool:
        """Validate that the input data meets panel data requirements.

        Args:
            data: DataFrame to validate.

        Returns:
            bool: True if data is valid, False otherwise.
        """
        if data is None or data.empty:
            self.logger.warning("Data is empty")
            return False

        required_cols = self.get_required_columns()
        missing_cols = [col for col in required_cols if col not in data.columns]

        if missing_cols:
            self.logger.warning(f"Missing required columns: {missing_cols}")
            return False

        return True

    def get_required_columns(self) -> List[str]:
        """Get required column names from config.

        Returns:
            List[str]: Column names that must be present in input data.
        """
        if not self.config:
            return ["unit_id", "date"]

        return [
            self.config["unit_column"],
            self.config["time_column"],
        ]
