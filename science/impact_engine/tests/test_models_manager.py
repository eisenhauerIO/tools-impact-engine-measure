"""Tests for ModelsManager with dependency injection."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

from impact_engine.models import (
    FitOutput,
    ModelInterface,
    ModelsManager,
    create_models_manager,
    create_models_manager_from_config,
)
from impact_engine.models.base import ModelResult
from impact_engine.models.factory import MODEL_REGISTRY


def complete_measurement_config(**overrides):
    """Create a complete MEASUREMENT config with defaults.

    Tests that bypass process_config() must provide complete configs.
    """
    config = {
        "MODEL": "mock",
        "PARAMS": {
            "intervention_date": "2024-01-15",
            "dependent_variable": "revenue",
        },
    }
    if overrides:
        config["PARAMS"].update(overrides)
    return config


class MockModel(ModelInterface):
    """Mock model for testing.

    Updated to return ModelResult (storage-agnostic pattern from Phase 1).
    """

    def __init__(self):
        self.is_connected = False
        self.config = None

    def connect(self, config):
        """Mock connect method."""
        self.config = config
        self.is_connected = True
        return True

    def validate_connection(self):
        """Mock validate_connection method."""
        return self.is_connected

    def validate_params(self, params):
        """Mock validate_params method (required by abstract base)."""
        # No validation for mock model
        pass

    def transform_outbound(self, data, intervention_date, **kwargs):
        """Mock transform_outbound method."""
        return {"data": data, "intervention_date": intervention_date, "kwargs": kwargs}

    def transform_inbound(self, model_results):
        """Mock transform_inbound method."""
        return {"model_type": "mock", "results": model_results}

    def fit(self, data: pd.DataFrame, intervention_date: str, **kwargs) -> ModelResult:
        """Mock fit method - returns ModelResult (storage handled by manager)."""
        if not self.is_connected:
            raise ConnectionError("Model not connected. Call connect() first.")

        return ModelResult(
            model_type="mock",
            data={
                "intervention_date": intervention_date,
                "rows_processed": len(data),
            },
        )

    def validate_data(self, data: pd.DataFrame) -> bool:
        """Mock validate_data method."""
        return not data.empty and "date" in data.columns

    def get_required_columns(self) -> list:
        """Mock get_required_columns method."""
        return ["date", "value"]


class TestModelsManagerDependencyInjection:
    """Tests for dependency injection pattern."""

    def test_create_with_injected_model(self):
        """Test creating manager with injected model."""
        mock_model = MockModel()
        config = complete_measurement_config()

        manager = ModelsManager(config, mock_model)

        assert manager.model is mock_model
        assert mock_model.is_connected is True

    def test_create_with_mock_spec(self):
        """Test creating manager with Mock(spec=ModelInterface)."""
        mock_model = Mock(spec=ModelInterface)
        mock_model.connect.return_value = True

        config = complete_measurement_config()

        manager = ModelsManager(config, mock_model)

        mock_model.connect.assert_called_once()
        assert manager.model is mock_model

    def test_model_receives_params_config(self):
        """Test that model receives PARAMS config on connect."""
        mock_model = MockModel()
        config = complete_measurement_config(order=(1, 0, 0))

        ModelsManager(config, mock_model)

        assert mock_model.config["intervention_date"] == "2024-01-15"
        assert mock_model.config["order"] == (1, 0, 0)


class TestModelsManagerConfiguration:
    """Tests for configuration handling.

    Note: Validation is now centralized in process_config().
    These tests verify the manager works with complete configs.
    """

    def test_get_current_config(self):
        """Test getting current configuration."""
        mock_model = MockModel()
        config = complete_measurement_config()

        manager = ModelsManager(config, mock_model)
        assert manager.get_current_config() == config


class TestModelsManagerFitModel:
    """Tests for model fitting functionality."""

    def test_fit_model_success(self):
        """Test successful model fitting returns FitOutput."""
        from artifact_store import ArtifactStore

        mock_model = MockModel()
        config = complete_measurement_config()

        manager = ModelsManager(config, mock_model)

        data = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10), "value": range(10)})

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ArtifactStore(tmpdir)
            fit_output = manager.fit_model(
                data=data,
                storage=storage,
            )

            assert isinstance(fit_output, FitOutput)
            assert fit_output.results_path.endswith(".json")
            assert fit_output.model_type == "mock"

    def test_fit_model_uses_config_intervention_date(self):
        """Test that fit_model uses intervention date from config."""
        from artifact_store import ArtifactStore

        mock_model = Mock(spec=ModelInterface)
        mock_model.connect.return_value = True
        mock_model.get_fit_params.side_effect = lambda p: p
        mock_model.fit.return_value = ModelResult(model_type="mock", data={"test": True})

        config = complete_measurement_config()
        manager = ModelsManager(config, mock_model)

        data = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10), "value": range(10)})

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ArtifactStore(tmpdir)
            manager.fit_model(data=data, storage=storage)

            # Verify fit was called with intervention_date from config
            call_kwargs = mock_model.fit.call_args[1]
            assert call_kwargs["intervention_date"] == "2024-01-15"

    def test_fit_model_missing_storage(self):
        """Test fit_model raises error when storage is missing."""
        mock_model = MockModel()
        config = complete_measurement_config()

        manager = ModelsManager(config, mock_model)

        data = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10), "value": range(10)})

        with pytest.raises(ValueError, match="Storage backend is required"):
            manager.fit_model(data=data, storage=None)

    def test_fit_model_with_explicit_params(self):
        """Test fit_model with explicitly provided parameters (overrides)."""
        from artifact_store import ArtifactStore

        mock_model = Mock(spec=ModelInterface)
        mock_model.connect.return_value = True
        mock_model.get_fit_params.side_effect = lambda p: p
        mock_model.fit.return_value = ModelResult(model_type="mock", data={"test": True})

        config = complete_measurement_config()
        manager = ModelsManager(config, mock_model)

        data = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10), "value": range(10)})

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ArtifactStore(tmpdir)
            manager.fit_model(
                data=data,
                storage=storage,
                intervention_date="2024-01-20",  # Override config
                dependent_variable="sales",
            )

            call_kwargs = mock_model.fit.call_args[1]
            assert call_kwargs["intervention_date"] == "2024-01-20"
            assert call_kwargs["dependent_variable"] == "sales"


class TestModelsFactory:
    """Tests for factory functions."""

    def test_create_models_manager_from_config_dict(self):
        """Test creating manager from config dict."""
        MODEL_REGISTRY.register("mock", MockModel)

        try:
            config = complete_measurement_config()

            manager = create_models_manager_from_config(config)

            assert isinstance(manager, ModelsManager)
            assert isinstance(manager.model, MockModel)
        finally:
            del MODEL_REGISTRY._registry["mock"]

    def test_create_models_manager_from_file(self):
        """Test creating manager from config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            products_path = str(Path(tmpdir) / "products.csv")
            pd.DataFrame({"product_id": ["p1"]}).to_csv(products_path, index=False)

            # Use new SOURCE/TRANSFORM config structure
            config = {
                "DATA": {
                    "SOURCE": {
                        "type": "simulator",
                        "CONFIG": {
                            "path": products_path,
                            "start_date": "2024-01-01",
                            "end_date": "2024-01-31",
                        },
                    },
                },
                "MEASUREMENT": {
                    "MODEL": "interrupted_time_series",
                    "PARAMS": {
                        "intervention_date": "2024-01-15",
                    },
                },
            }
            config_path = str(Path(tmpdir) / "config.json")
            with open(config_path, "w") as f:
                json.dump(config, f)

            manager = create_models_manager(config_path)

            assert isinstance(manager, ModelsManager)
            # Config now has defaults merged, so check key values are present
            assert manager.measurement_config["MODEL"] == "interrupted_time_series"
            assert manager.measurement_config["PARAMS"]["intervention_date"] == "2024-01-15"

    def test_create_models_manager_unknown_type(self):
        """Test creating manager with unknown model type."""
        config = complete_measurement_config()
        config["MODEL"] = "unknown_model"

        with pytest.raises(ValueError, match="Unknown model"):
            create_models_manager_from_config(config)

    def test_register_invalid_model(self):
        """Test registering invalid model class."""

        class InvalidModel:
            pass

        with pytest.raises(ValueError, match="must implement ModelInterface"):
            MODEL_REGISTRY.register("invalid", InvalidModel)


class TestModelsManagerParamFiltering:
    """Tests for get_fit_params integration in fit_model."""

    def test_fit_model_filters_params_via_get_fit_params(self):
        """Verify manager calls get_fit_params and fit receives filtered result."""
        from artifact_store import ArtifactStore

        mock_model = Mock(spec=ModelInterface)
        mock_model.connect.return_value = True
        mock_model.get_fit_params.return_value = {"intervention_date": "2024-01-15"}
        mock_model.fit.return_value = ModelResult(model_type="mock", data={"test": True})

        config = complete_measurement_config()
        manager = ModelsManager(config, mock_model)

        data = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10), "value": range(10)})

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ArtifactStore(tmpdir)
            manager.fit_model(data=data, storage=storage)

            # get_fit_params was called with the full params dict
            mock_model.get_fit_params.assert_called_once()
            full_params = mock_model.get_fit_params.call_args[0][0]
            assert "intervention_date" in full_params
            assert "dependent_variable" in full_params

            # fit received data + only the filtered params
            call_kwargs = mock_model.fit.call_args[1]
            assert call_kwargs["intervention_date"] == "2024-01-15"
            assert "dependent_variable" not in call_kwargs

    def test_validate_params_receives_full_params(self):
        """Verify validation sees all params before filtering."""
        from artifact_store import ArtifactStore

        mock_model = Mock(spec=ModelInterface)
        mock_model.connect.return_value = True
        mock_model.get_fit_params.return_value = {}
        mock_model.fit.return_value = ModelResult(model_type="mock", data={"test": True})

        config = complete_measurement_config()
        manager = ModelsManager(config, mock_model)

        data = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10), "value": range(10)})

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ArtifactStore(tmpdir)
            manager.fit_model(data=data, storage=storage)

            # validate_params received the full unfiltered params
            validate_params = mock_model.validate_params.call_args[0][0]
            assert "intervention_date" in validate_params
            assert "dependent_variable" in validate_params

    def test_overrides_subject_to_filtering(self):
        """Verify caller overrides are also filtered."""
        from artifact_store import ArtifactStore

        mock_model = Mock(spec=ModelInterface)
        mock_model.connect.return_value = True
        # Filter removes everything except intervention_date
        mock_model.get_fit_params.side_effect = lambda p: {
            k: v for k, v in p.items() if k == "intervention_date"
        }
        mock_model.fit.return_value = ModelResult(model_type="mock", data={"test": True})

        config = complete_measurement_config()
        manager = ModelsManager(config, mock_model)

        data = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10), "value": range(10)})

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ArtifactStore(tmpdir)
            manager.fit_model(
                data=data,
                storage=storage,
                custom_param="should_be_filtered",
            )

            call_kwargs = mock_model.fit.call_args[1]
            assert "custom_param" not in call_kwargs
            assert call_kwargs["intervention_date"] == "2024-01-15"


class TestModelsManagerConnectionFailure:
    """Tests for connection failure handling."""

    def test_connection_failure_raises_error(self):
        """Test that connection failure raises ConnectionError."""
        mock_model = Mock(spec=ModelInterface)
        mock_model.connect.return_value = False

        config = complete_measurement_config()

        with pytest.raises(ConnectionError, match="Failed to connect"):
            ModelsManager(config, mock_model)
