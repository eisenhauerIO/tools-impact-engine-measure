"""Tests for ExperimentAdapter."""

import numpy as np
import pandas as pd
import pytest

from impact_engine.models.base import ModelResult
from impact_engine.models.conftest import merge_model_params
from impact_engine.models.experiment import ExperimentAdapter


class TestExperimentAdapterConnect:
    """Tests for connect() method."""

    def test_connect_success(self):
        """Test successful model connection."""
        model = ExperimentAdapter()
        config = merge_model_params({"formula": "y ~ treatment"})

        result = model.connect(config)

        assert result is True
        assert model.is_connected is True
        assert model.config["formula"] == "y ~ treatment"

    def test_connect_missing_formula(self):
        """Test connection with missing formula."""
        model = ExperimentAdapter()
        config = merge_model_params({})

        with pytest.raises(ValueError, match="formula is required"):
            model.connect(config)

    def test_connect_invalid_formula_type(self):
        """Test connection with non-string formula."""
        model = ExperimentAdapter()
        config = merge_model_params({"formula": 123})

        with pytest.raises(ValueError, match="formula is required and must be a string"):
            model.connect(config)


class TestExperimentAdapterValidateParams:
    """Tests for validate_params() method."""

    def test_validate_params_valid(self):
        """Test validation with valid params."""
        model = ExperimentAdapter()
        model.validate_params({"formula": "y ~ treatment"})

    def test_validate_params_missing_formula(self):
        """Test validation with missing formula."""
        model = ExperimentAdapter()

        with pytest.raises(ValueError, match="formula is required"):
            model.validate_params({})


class TestExperimentAdapterFit:
    """Tests for fit() method."""

    @pytest.fixture()
    def connected_model(self):
        """Return a connected ExperimentAdapter."""
        model = ExperimentAdapter()
        model.connect(merge_model_params({"formula": "y ~ treatment + x1"}))
        return model

    @pytest.fixture()
    def sample_data(self):
        """Return sample experimental data."""
        rng = np.random.default_rng(42)
        n = 100
        treatment = rng.integers(0, 2, size=n)
        x1 = rng.normal(0, 1, size=n)
        y = 5.0 + 2.0 * treatment + 1.5 * x1 + rng.normal(0, 0.5, size=n)
        return pd.DataFrame({"y": y, "treatment": treatment, "x1": x1})

    def test_fit_not_connected(self, sample_data):
        """Test fitting without connection."""
        model = ExperimentAdapter()

        with pytest.raises(ConnectionError, match="Model not connected"):
            model.fit(sample_data)

    def test_fit_returns_model_result(self, connected_model, sample_data):
        """Test that fit returns ModelResult."""
        result = connected_model.fit(sample_data)

        assert isinstance(result, ModelResult)
        assert result.model_type == "experiment"

    def test_fit_result_data_structure(self, connected_model, sample_data):
        """Test that fit result has expected data keys."""
        result = connected_model.fit(sample_data)

        assert "formula" in result.data
        assert "impact_estimates" in result.data
        assert result.data["formula"] == "y ~ treatment + x1"

    def test_fit_impact_estimates_structure(self, connected_model, sample_data):
        """Test that impact_estimates has all expected fields."""
        result = connected_model.fit(sample_data)
        estimates = result.data["impact_estimates"]

        assert "params" in estimates
        assert "bse" in estimates
        assert "tvalues" in estimates
        assert "pvalues" in estimates
        assert "conf_int" in estimates
        assert "rsquared" in estimates
        assert "rsquared_adj" in estimates
        assert "fvalue" in estimates
        assert "f_pvalue" in estimates
        assert "nobs" in estimates
        assert "df_resid" in estimates

    def test_fit_coefficients_keys(self, connected_model, sample_data):
        """Test that coefficient dicts have expected variable names."""
        result = connected_model.fit(sample_data)
        params = result.data["impact_estimates"]["params"]

        assert "Intercept" in params
        assert "treatment" in params
        assert "x1" in params

    def test_fit_values_are_numeric(self, connected_model, sample_data):
        """Test that all values are JSON-serializable numeric types."""
        result = connected_model.fit(sample_data)
        estimates = result.data["impact_estimates"]

        for key in ("rsquared", "rsquared_adj", "fvalue", "f_pvalue", "df_resid"):
            assert isinstance(estimates[key], float)
        assert isinstance(estimates["nobs"], int)

        for var_dict in (estimates["params"], estimates["bse"], estimates["tvalues"]):
            for v in var_dict.values():
                assert isinstance(v, float)

    def test_fit_conf_int_structure(self, connected_model, sample_data):
        """Test that confidence intervals have correct structure."""
        result = connected_model.fit(sample_data)
        conf_int = result.data["impact_estimates"]["conf_int"]

        for var in ("Intercept", "treatment", "x1"):
            assert var in conf_int
            assert len(conf_int[var]) == 2
            assert conf_int[var][0] < conf_int[var][1]

    def test_fit_with_robust_se(self, connected_model, sample_data):
        """Test pass-through of kwargs to statsmodels .fit()."""
        result = connected_model.fit(sample_data, cov_type="HC3")

        assert isinstance(result, ModelResult)
        assert result.data["impact_estimates"]["nobs"] == 100

    def test_fit_model_summary_merged(self, connected_model, sample_data):
        """Test that model-level stats are in impact_estimates (no separate model_summary)."""
        result = connected_model.fit(sample_data)

        assert "model_summary" not in result.data
        assert result.data["impact_estimates"]["nobs"] == 100
        assert 0.0 <= result.data["impact_estimates"]["rsquared"] <= 1.0


class TestExperimentAdapterValidateData:
    """Tests for validate_data() method."""

    def test_valid_data(self):
        """Test validation with valid data."""
        model = ExperimentAdapter()
        data = pd.DataFrame({"y": [1, 2], "x": [3, 4]})

        assert model.validate_data(data) is True

    def test_empty_dataframe(self):
        """Test validation with empty DataFrame."""
        model = ExperimentAdapter()
        data = pd.DataFrame()

        assert model.validate_data(data) is False


class TestExperimentAdapterGetRequiredColumns:
    """Tests for get_required_columns() method."""

    def test_required_columns(self):
        """Test that required columns is empty (statsmodels validates natively)."""
        model = ExperimentAdapter()

        assert model.get_required_columns() == []
