"""Synthetic Control Model Adapter - thin wrapper around pysyncon's Synth."""

import logging
from typing import Any, Dict, List

import pandas as pd

from ..base import ModelInterface, ModelResult
from ..factory import MODEL_REGISTRY


@MODEL_REGISTRY.register_decorator("synthetic_control")
class SyntheticControlAdapter(ModelInterface):
    """Estimates causal impact using the synthetic control method via pysyncon.

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
                "outcome_column is required and must be a string. " "Specify in MEASUREMENT.PARAMS configuration."
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
            import pysyncon  # noqa: F401

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
                "treated_unit is required for SyntheticControlAdapter. " "Specify in MEASUREMENT.PARAMS configuration."
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
            "optim_method",
            "optim_initial",
        }
    )

    def get_fit_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """SC accepts treatment_time, treated_unit, columns, and optimizer params."""
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
                - optim_method (str): Optimization method (default: "Nelder-Mead").
                - optim_initial (str): Initial weight strategy (default: "equal").

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
            raise ValueError(f"Data validation failed. Required columns: {self.get_required_columns()}")

        try:
            from pysyncon import Dataprep, Synth

            # Read params from kwargs (already filtered by get_fit_params)
            treatment_time = kwargs["treatment_time"]
            treated_unit = str(kwargs["treated_unit"])
            unit_column = kwargs.get("unit_column", self.config["unit_column"])
            time_column = kwargs.get("time_column", self.config["time_column"])
            outcome_column = kwargs.get("outcome_column", self.config["outcome_column"])

            optim_method = kwargs.get("optim_method", "Nelder-Mead")
            optim_initial = kwargs.get("optim_initial", "equal")

            # Ensure time column is datetime for consistent comparison
            df = data.copy()
            df[time_column] = pd.to_datetime(df[time_column])
            treatment_time = pd.Timestamp(treatment_time)

            # Identify control units: all units except the treated unit
            all_units = df[unit_column].unique().tolist()
            control_units = [str(u) for u in all_units if str(u) != treated_unit]

            if not control_units:
                raise ValueError("No control units found in data")

            # Pre- and post-treatment time ranges
            all_times = sorted(df[time_column].unique())
            pre_times = [t for t in all_times if t < treatment_time]
            post_times = [t for t in all_times if t >= treatment_time]
            n_pre = len(pre_times)
            n_post = len(post_times)

            self.logger.info(
                f"Fitting SyntheticControl: treated={treated_unit}, "
                f"n_control={len(control_units)}, "
                f"n_pre={n_pre}, n_post={n_post}"
            )

            # Build Dataprep — pysyncon's data description object
            dataprep = Dataprep(
                foo=df,
                predictors=[outcome_column],
                predictors_op="mean",
                dependent=outcome_column,
                unit_variable=unit_column,
                time_variable=time_column,
                treatment_identifier=treated_unit,
                controls_identifier=control_units,
                time_predictors_prior=pre_times,
                time_optimize_ssr=pre_times,
            )

            # Fit via optimization
            synth = Synth()
            synth.fit(
                dataprep=dataprep,
                optim_method=optim_method,
                optim_initial=optim_initial,
            )

            # Extract results
            att_result = synth.att(time_period=post_times)
            att = float(att_result["att"])
            se = float(att_result["se"])

            weights = synth.weights(round=4)
            mspe = float(synth.mspe())
            mae = float(synth.mae())

            impact_estimates = {
                "att": att,
                "se": se,
                "ci_lower": att - 1.96 * se,
                "ci_upper": att + 1.96 * se,
                "cumulative_effect": att * n_post,
            }

            model_summary = {
                "n_pre_periods": n_pre,
                "n_post_periods": n_post,
                "n_control_units": len(control_units),
                "mspe": mspe,
                "mae": mae,
                "weights": weights.to_dict(),
            }

            self.logger.info(f"SyntheticControl fit complete: att={impact_estimates['att']:.4f}")

            return ModelResult(
                model_type="synthetic_control",
                data={
                    "model_params": {
                        "treatment_time": str(treatment_time),
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
