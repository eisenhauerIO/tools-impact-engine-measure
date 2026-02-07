"""Subclassification (stratification) estimator for treatment effects.

This model stratifies observations on covariates using propensity-score quantiles,
computes within-stratum treated/control mean differences, and aggregates via
weighted average to estimate ATT or ATE.

The underlying "library" is pandas groupby + numpy arithmetic — the algorithm is
simple enough that wrapping an external causal-inference package would add
dependency weight with no statistical benefit.
"""

import logging
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from ..base import ModelInterface, ModelResult
from ..factory import MODEL_REGISTRY


@MODEL_REGISTRY.register_decorator("subclassification")
class SubclassificationAdapter(ModelInterface):
    """Estimates treatment effects via subclassification on covariates.

    Constraints:
    - Data must contain a binary treatment column
    - One or more covariate columns must be specified
    - treatment_column and covariate_columns are required in MEASUREMENT.PARAMS
    """

    def __init__(self):
        """Initialize the SubclassificationAdapter."""
        self.logger = logging.getLogger(__name__)
        self.is_connected = False
        self.config = None

    def connect(self, config: Dict[str, Any]) -> bool:
        """Initialize model with configuration parameters.

        Config is pre-validated with defaults merged via process_config().
        """
        n_strata = config.get("n_strata", 5)
        if not isinstance(n_strata, int) or n_strata < 1:
            raise ValueError("n_strata must be a positive integer")

        estimand = config.get("estimand", "att")
        if estimand not in ("att", "ate"):
            raise ValueError("estimand must be 'att' or 'ate'")

        treatment_column = config.get("treatment_column")
        if not treatment_column:
            raise ValueError(
                "treatment_column is required for SubclassificationAdapter. "
                "Specify in MEASUREMENT.PARAMS configuration."
            )

        covariate_columns = config.get("covariate_columns")
        if not covariate_columns:
            raise ValueError(
                "covariate_columns is required for SubclassificationAdapter. "
                "Specify in MEASUREMENT.PARAMS configuration."
            )
        if isinstance(covariate_columns, str):
            covariate_columns = [covariate_columns]

        self.config = {
            "n_strata": n_strata,
            "estimand": estimand,
            "treatment_column": treatment_column,
            "covariate_columns": list(covariate_columns),
            "dependent_variable": config.get("dependent_variable", "revenue"),
        }
        self.is_connected = True
        return True

    def validate_connection(self) -> bool:
        """Validate that the model is properly initialized and ready to use."""
        return self.is_connected and self.config is not None

    def validate_params(self, params: Dict[str, Any]) -> None:
        """Validate subclassification-specific parameters.

        Args:
            params: Parameters dict forwarded from config.

        Raises:
            ValueError: If required parameters are missing.
        """
        if not params.get("treatment_column"):
            raise ValueError(
                "treatment_column is required for SubclassificationAdapter. "
                "Specify in MEASUREMENT.PARAMS configuration."
            )
        if not params.get("covariate_columns"):
            raise ValueError(
                "covariate_columns is required for SubclassificationAdapter. "
                "Specify in MEASUREMENT.PARAMS configuration."
            )

    def fit(self, data: pd.DataFrame, **kwargs) -> ModelResult:
        """Fit the subclassification model and return results.

        Args:
            data: DataFrame with treatment indicator, covariates, and outcome.
            **kwargs: All MEASUREMENT.PARAMS forwarded by the manager, plus storage.

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
        storage = kwargs.get("storage")

        if not self.validate_data(data):
            raise ValueError(
                f"Data validation failed. Required columns: " f"{self.get_required_columns()}"
            )

        try:
            # 1. Stratify observations on covariates
            stratified, actual_strata = self._stratify(data)

            # 2. Compute per-stratum treatment effects
            stratum_effects = self._compute_stratum_effects(stratified, dependent_variable)

            # 3. Handle all-strata-dropped edge case
            if stratum_effects.empty:
                self.logger.warning(
                    "All strata dropped due to lack of common support. "
                    "Returning zero-effect result."
                )
                return self._empty_result()

            # 4. Aggregate stratum effects into overall estimate
            treatment_effect = self._aggregate_effects(stratum_effects)

            # 5. Write supplementary stratum details
            if storage:
                storage.write_parquet("stratum_details.parquet", stratum_effects)

            # 6. Build result
            treatment_col = self.config["treatment_column"]
            n_treated = int((data[treatment_col] == 1).sum())
            n_control = int((data[treatment_col] == 0).sum())

            return ModelResult(
                model_type="subclassification",
                data={
                    "dependent_variable": dependent_variable,
                    "impact_estimates": {
                        "treatment_effect": float(treatment_effect),
                        "n_strata": int(len(stratum_effects)),
                        "n_strata_dropped": int(actual_strata - len(stratum_effects)),
                    },
                    "model_summary": {
                        "n_observations": int(len(data)),
                        "n_treated": n_treated,
                        "n_control": n_control,
                        "estimand": self.config["estimand"],
                    },
                },
            )

        except Exception as e:
            self.logger.error(f"Error fitting SubclassificationAdapter: {e}")
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

    def _stratify(self, data: pd.DataFrame) -> tuple:
        """Bin observations into strata using covariate quantiles.

        Uses pd.qcut on each covariate, then creates a composite stratum label
        by concatenating per-covariate bin indices.

        Args:
            data: DataFrame with covariate columns.

        Returns:
            Tuple of (DataFrame with '_stratum' column, number of unique strata).
        """
        df = data.copy()
        n_strata = self.config["n_strata"]
        covariate_columns = self.config["covariate_columns"]

        bin_labels = []
        for col in covariate_columns:
            try:
                bins = pd.qcut(df[col], q=n_strata, labels=False, duplicates="drop")
            except ValueError:
                # All values identical — single bin
                bins = pd.Series(0, index=df.index)

            actual_bins = int(bins.nunique())
            if actual_bins < n_strata:
                self.logger.warning(
                    f"Covariate '{col}': requested {n_strata} bins but got "
                    f"{actual_bins} due to duplicate quantile edges."
                )
            bin_labels.append(bins.astype(str))

        # Composite stratum label
        df["_stratum"] = bin_labels[0]
        for bl in bin_labels[1:]:
            df["_stratum"] = df["_stratum"] + "_" + bl

        actual_strata = df["_stratum"].nunique()
        return df, actual_strata

    def _compute_stratum_effects(self, data: pd.DataFrame, dependent_variable: str) -> pd.DataFrame:
        """Compute per-stratum treated/control means and differences.

        Drops strata without both treated and control observations (common
        support violation) and logs a warning.

        Args:
            data: DataFrame with '_stratum' column and treatment indicator.
            dependent_variable: Outcome column name.

        Returns:
            DataFrame with columns: stratum, n_treated, n_control,
            mean_treated, mean_control, effect.
        """
        treatment_col = self.config["treatment_column"]

        records = []
        for stratum, group in data.groupby("_stratum"):
            treated = group[group[treatment_col] == 1]
            control = group[group[treatment_col] == 0]

            if treated.empty or control.empty:
                self.logger.warning(
                    f"Stratum '{stratum}' lacks common support "
                    f"(treated={len(treated)}, control={len(control)}). "
                    "Dropping."
                )
                continue

            mean_t = treated[dependent_variable].mean()
            mean_c = control[dependent_variable].mean()

            records.append(
                {
                    "stratum": stratum,
                    "n_treated": int(len(treated)),
                    "n_control": int(len(control)),
                    "mean_treated": float(mean_t),
                    "mean_control": float(mean_c),
                    "effect": float(mean_t - mean_c),
                }
            )

        return pd.DataFrame(records)

    def _aggregate_effects(self, stratum_effects: pd.DataFrame) -> float:
        """Aggregate per-stratum effects into an overall treatment effect.

        Weights depend on the estimand:
        - ATT: weight by n_treated in each stratum
        - ATE: weight by total observations (n_treated + n_control) in each stratum

        Args:
            stratum_effects: DataFrame from _compute_stratum_effects().

        Returns:
            Weighted average treatment effect.
        """
        estimand = self.config["estimand"]

        if estimand == "att":
            weights = stratum_effects["n_treated"]
        else:  # ate
            weights = stratum_effects["n_treated"] + stratum_effects["n_control"]

        return float(np.average(stratum_effects["effect"], weights=weights))

    def _empty_result(self) -> ModelResult:
        """Return zero-effect ModelResult when all strata are dropped.

        This enables pipeline execution with edge-case data without errors.
        """
        return ModelResult(
            model_type="subclassification",
            data={
                "dependent_variable": self.config["dependent_variable"],
                "impact_estimates": {
                    "treatment_effect": 0.0,
                    "n_strata": 0,
                    "n_strata_dropped": 0,
                },
                "model_summary": {
                    "n_observations": 0,
                    "n_treated": 0,
                    "n_control": 0,
                    "estimand": self.config["estimand"],
                },
            },
        )
