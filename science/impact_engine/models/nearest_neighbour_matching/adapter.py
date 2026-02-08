"""Nearest neighbour matching estimator for treatment effects.

Thin wrapper around causalml's NearestNeighborMatch. Matches treated and control
units on observed covariates, then computes ATT, ATC, and ATE from mean outcome
differences in the matched sample. Covariate balance (SMD before/after) is stored
as an artifact.
"""

import logging
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from causalml.match import NearestNeighborMatch, create_table_one

from ..base import ModelInterface, ModelResult
from ..factory import MODEL_REGISTRY


@MODEL_REGISTRY.register_decorator("nearest_neighbour_matching")
class NearestNeighbourMatchingAdapter(ModelInterface):
    """Estimates treatment effects via nearest neighbour matching on covariates.

    Constraints:
    - Data must contain a binary treatment column
    - One or more covariate columns must be specified
    - treatment_column and covariate_columns are required in MEASUREMENT.PARAMS
    - When replace=False, only single-column matching is supported (causalml constraint)
    """

    def __init__(self):
        """Initialize the NearestNeighbourMatchingAdapter."""
        self.logger = logging.getLogger(__name__)
        self.is_connected = False
        self.config = None

    def connect(self, config: Dict[str, Any]) -> bool:
        """Initialize model with configuration parameters.

        Config is pre-validated with defaults merged via process_config().
        """
        treatment_column = config.get("treatment_column")
        if not treatment_column:
            raise ValueError(
                "treatment_column is required for NearestNeighbourMatchingAdapter. "
                "Specify in MEASUREMENT.PARAMS configuration."
            )

        covariate_columns = config.get("covariate_columns")
        if not covariate_columns:
            raise ValueError(
                "covariate_columns is required for NearestNeighbourMatchingAdapter. "
                "Specify in MEASUREMENT.PARAMS configuration."
            )
        if isinstance(covariate_columns, str):
            covariate_columns = [covariate_columns]

        caliper = config.get("caliper", 0.2)
        if not isinstance(caliper, (int, float)) or caliper <= 0:
            raise ValueError("caliper must be a positive number")

        ratio = config.get("ratio", 1)
        if not isinstance(ratio, int) or ratio < 1:
            raise ValueError("ratio must be a positive integer")

        self.config = {
            "treatment_column": treatment_column,
            "covariate_columns": list(covariate_columns),
            "dependent_variable": config.get("dependent_variable", "revenue"),
            "caliper": float(caliper),
            "replace": bool(config.get("replace", False)),
            "ratio": ratio,
            "shuffle": bool(config.get("shuffle", True)),
            "random_state": config.get("random_state"),
            "n_jobs": int(config.get("n_jobs", 1)),
        }
        self.is_connected = True
        return True

    def validate_connection(self) -> bool:
        """Validate that the model is properly initialized and ready to use."""
        if not self.is_connected or self.config is None:
            return False

        try:
            from causalml.match import NearestNeighborMatch  # noqa: F401

            return True
        except ImportError:
            return False

    def validate_params(self, params: Dict[str, Any]) -> None:
        """Validate nearest-neighbour-matching-specific parameters.

        Args:
            params: Parameters dict forwarded from config.

        Raises:
            ValueError: If required parameters are missing.
        """
        if not params.get("treatment_column"):
            raise ValueError(
                "treatment_column is required for NearestNeighbourMatchingAdapter. "
                "Specify in MEASUREMENT.PARAMS configuration."
            )
        if not params.get("covariate_columns"):
            raise ValueError(
                "covariate_columns is required for NearestNeighbourMatchingAdapter. "
                "Specify in MEASUREMENT.PARAMS configuration."
            )

    _FIT_PARAMS = frozenset({"dependent_variable"})

    def get_fit_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Nearest neighbour matching only uses dependent_variable from fit kwargs."""
        return {k: v for k, v in params.items() if k in self._FIT_PARAMS}

    def fit(self, data: pd.DataFrame, **kwargs) -> ModelResult:
        """Fit the nearest neighbour matching model and return results.

        Performs two matching passes (ATT and ATC) and computes ATE as the
        weighted combination.

        Args:
            data: DataFrame with treatment indicator, covariates, and outcome.
            **kwargs: Filtered MEASUREMENT.PARAMS forwarded by the manager.

        Returns:
            ModelResult: Standardized result container.

        Raises:
            ConnectionError: If model not connected.
            ValueError: If data validation fails.
            RuntimeError: If model fitting fails.
        """
        if not self.is_connected:
            raise ConnectionError("Model not connected. Call connect() first.")

        dependent_variable = kwargs.get("dependent_variable", self.config["dependent_variable"])

        if not self.validate_data(data):
            raise ValueError(
                f"Data validation failed. Required columns: " f"{self.get_required_columns()}"
            )

        try:
            treatment_col = self.config["treatment_column"]
            score_cols = self.config["covariate_columns"]
            n_total = len(data)
            n_treated = int((data[treatment_col] == 1).sum())
            n_control = int((data[treatment_col] == 0).sum())

            # Common matching params (excluding direction-specific ones)
            match_kwargs = {
                "caliper": self.config["caliper"],
                "replace": self.config["replace"],
                "ratio": self.config["ratio"],
                "shuffle": self.config["shuffle"],
                "random_state": self.config["random_state"],
                "n_jobs": self.config["n_jobs"],
            }

            # --- ATT: match control to each treated unit ---
            matcher_att = NearestNeighborMatch(treatment_to_control=True, **match_kwargs)
            matched_att = matcher_att.match(data, treatment_col, score_cols)
            att = float(
                matched_att.loc[matched_att[treatment_col] == 1, dependent_variable].mean()
                - matched_att.loc[matched_att[treatment_col] == 0, dependent_variable].mean()
            )

            # --- ATC: match treated to each control unit ---
            matcher_atc = NearestNeighborMatch(treatment_to_control=False, **match_kwargs)
            matched_atc = matcher_atc.match(data, treatment_col, score_cols)
            atc = float(
                matched_atc.loc[matched_atc[treatment_col] == 1, dependent_variable].mean()
                - matched_atc.loc[matched_atc[treatment_col] == 0, dependent_variable].mean()
            )

            # --- ATE: weighted combination ---
            ate = att * (n_treated / n_total) + atc * (n_control / n_total)

            # --- Standard errors (simple SE of matched mean differences) ---
            att_se = self._matched_se(matched_att, treatment_col, dependent_variable)
            atc_se = self._matched_se(matched_atc, treatment_col, dependent_variable)

            # --- Covariate balance ---
            balance_before = create_table_one(data, treatment_col, score_cols)
            balance_after = create_table_one(matched_att, treatment_col, score_cols)

            self.logger.info(
                f"Nearest neighbour matching complete: "
                f"ATT={att:.4f}, ATC={atc:.4f}, ATE={ate:.4f}, "
                f"n_matched_att={len(matched_att)}, n_matched_atc={len(matched_atc)}"
            )

            return ModelResult(
                model_type="nearest_neighbour_matching",
                data={
                    "dependent_variable": dependent_variable,
                    "impact_estimates": {
                        "att": float(att),
                        "atc": float(atc),
                        "ate": float(ate),
                        "att_se": float(att_se),
                        "atc_se": float(atc_se),
                    },
                    "model_summary": {
                        "n_observations": int(n_total),
                        "n_treated": n_treated,
                        "n_control": n_control,
                        "n_matched_att": int(len(matched_att)),
                        "n_matched_atc": int(len(matched_atc)),
                        "caliper": float(self.config["caliper"]),
                        "replace": self.config["replace"],
                        "ratio": self.config["ratio"],
                    },
                },
                artifacts={
                    "matched_data_att": matched_att,
                    "balance_before": balance_before,
                    "balance_after": balance_after,
                },
            )

        except Exception as e:
            self.logger.error(f"Error fitting NearestNeighbourMatchingAdapter: {e}")
            raise RuntimeError(f"Model fitting failed: {e}") from e

    def validate_data(self, data: pd.DataFrame) -> bool:
        """Validate input data meets model requirements.

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
        """Get required column names.

        Returns:
            List[str]: Column names that must be present in input data.
        """
        if not self.config:
            return []
        return [self.config["treatment_column"]] + self.config["covariate_columns"]

    # ── Private helpers ──────────────────────────────────────────────

    @staticmethod
    def _matched_se(matched: pd.DataFrame, treatment_col: str, outcome_col: str) -> float:
        """Compute standard error of the matched mean difference.

        Uses the pooled SE formula: sqrt(var_t/n_t + var_c/n_c).

        Args:
            matched: Matched DataFrame from NearestNeighborMatch.match().
            treatment_col: Name of the treatment indicator column.
            outcome_col: Name of the outcome column.

        Returns:
            Standard error of the mean difference.
        """
        treated = matched.loc[matched[treatment_col] == 1, outcome_col]
        control = matched.loc[matched[treatment_col] == 0, outcome_col]

        if len(treated) < 2 or len(control) < 2:
            return float("nan")

        return float(np.sqrt(treated.var() / len(treated) + control.var() / len(control)))
