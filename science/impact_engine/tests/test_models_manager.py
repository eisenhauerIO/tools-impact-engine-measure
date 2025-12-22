"""Tests for ModelsManager with dependency injection."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

from impact_engine.models import (
    Model,
    ModelsManager,
    create_models_manager,
    create_models_manager_from_config,
)
from impact_engine.models.factory import MODEL_ADAPTERS, register_model_adapter


class MockModel(Model):
    """Mock model for testing."""

    def __init__(self):
        self.is_connected = False
        self.config = None
        self.storage = None

    def connect(self, config):
        """Mock connect method."""
        self.config = config
        self.is_connected = True
        return True

    def validate_connection(self):
        """Mock validate_connection method."""
        return self.is_connected

    def transform_outbound(self, data, intervention_date, **kwargs):
        """Mock transform_outbound method."""
        return {"data": data, "intervention_date": intervention_date, "kwargs": kwargs}

    def transform_inbound(self, model_results):
        """Mock transform_inbound method."""
        return {"model_type": "mock", "results": model_results}

    def fit(self, data: pd.DataFrame, intervention_date: str, output_path: str, **kwargs) -> str:
        """Mock fit method."""
        if not self.is_connected:
            raise ConnectionError("Model not connected. Call connect() first.")

        if not self.storage:
            raise ValueError("Storage backend is required but not configured")

        result_data = {
            "model_type": "mock",
            "intervention_date": intervention_date,
            "rows_processed": len(data),
        }

        result_path = f"{output_path}/mock_results.json"
        self.storage.write_json(result_path, result_data)
        stored_path = self.storage.full_path(result_path)

        return stored_path

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
        config = {"PARAMS": {"INTERVENTION_DATE": "2024-01-15"}}

        manager = ModelsManager(config, mock_model)

        assert manager.model is mock_model
        assert mock_model.is_connected is True

    def test_create_with_mock_spec(self):
        """Test creating manager with Mock(spec=Model)."""
        mock_model = Mock(spec=Model)
        mock_model.connect.return_value = True

        config = {"PARAMS": {"INTERVENTION_DATE": "2024-01-15"}}

        manager = ModelsManager(config, mock_model)

        mock_model.connect.assert_called_once()
        assert manager.model is mock_model

    def test_model_receives_params_config(self):
        """Test that model receives PARAMS config on connect."""
        mock_model = MockModel()
        params = {"INTERVENTION_DATE": "2024-01-15", "order": (1, 0, 0)}
        config = {"PARAMS": params}

        ModelsManager(config, mock_model)

        assert mock_model.config == params


class TestModelsManagerConfiguration:
    """Tests for configuration handling."""

    def test_validate_config_missing_params(self):
        """Test validation with missing PARAMS field."""
        mock_model = MockModel()
        with pytest.raises(ValueError, match="Missing required field 'PARAMS'"):
            ModelsManager({}, mock_model)

    def test_get_current_config(self):
        """Test getting current configuration."""
        mock_model = MockModel()
        config = {"PARAMS": {"INTERVENTION_DATE": "2024-01-15"}}

        manager = ModelsManager(config, mock_model)
        assert manager.get_current_config() == config


class TestModelsManagerFitModel:
    """Tests for model fitting functionality."""

    def test_fit_model_success(self):
        """Test successful model fitting."""
        from artifact_store import ArtifactStore

        mock_model = MockModel()
        config = {"PARAMS": {"INTERVENTION_DATE": "2024-01-15"}}

        manager = ModelsManager(config, mock_model)

        data = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10), "value": range(10)})

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ArtifactStore(tmpdir)
            result_path = manager.fit_model(
                data=data,
                output_path="results",
                storage=storage,
            )

            assert result_path.endswith(".json")

    def test_fit_model_uses_config_intervention_date(self):
        """Test that fit_model uses intervention date from config."""
        from artifact_store import ArtifactStore

        mock_model = Mock(spec=Model)
        mock_model.connect.return_value = True
        mock_model.fit.return_value = "/path/to/results.json"

        config = {"PARAMS": {"INTERVENTION_DATE": "2024-01-15"}}
        manager = ModelsManager(config, mock_model)

        data = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10), "value": range(10)})

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ArtifactStore(tmpdir)
            manager.fit_model(data=data, output_path="results", storage=storage)

            # Verify fit was called with intervention_date from config
            call_kwargs = mock_model.fit.call_args[1]
            assert call_kwargs["intervention_date"] == "2024-01-15"

    def test_fit_model_missing_intervention_date(self):
        """Test fit_model raises error when intervention date is missing."""
        mock_model = MockModel()
        config = {"PARAMS": {}}  # No INTERVENTION_DATE

        manager = ModelsManager(config, mock_model)

        data = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10), "value": range(10)})

        with tempfile.TemporaryDirectory() as tmpdir:
            from artifact_store import ArtifactStore

            storage = ArtifactStore(tmpdir)

            with pytest.raises(ValueError, match="INTERVENTION_DATE must be specified"):
                manager.fit_model(data=data, output_path="results", storage=storage)

    def test_fit_model_missing_storage(self):
        """Test fit_model raises error when storage is missing."""
        mock_model = MockModel()
        config = {"PARAMS": {"INTERVENTION_DATE": "2024-01-15"}}

        manager = ModelsManager(config, mock_model)

        data = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10), "value": range(10)})

        with pytest.raises(ValueError, match="Storage backend is required"):
            manager.fit_model(data=data, output_path="results", storage=None)

    def test_fit_model_with_explicit_params(self):
        """Test fit_model with explicitly provided parameters."""
        from artifact_store import ArtifactStore

        mock_model = Mock(spec=Model)
        mock_model.connect.return_value = True
        mock_model.fit.return_value = "/path/to/results.json"

        config = {"PARAMS": {"INTERVENTION_DATE": "2024-01-15"}}
        manager = ModelsManager(config, mock_model)

        data = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10), "value": range(10)})

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ArtifactStore(tmpdir)
            manager.fit_model(
                data=data,
                intervention_date="2024-01-20",  # Override config
                dependent_variable="sales",
                output_path="results",
                storage=storage,
            )

            call_kwargs = mock_model.fit.call_args[1]
            assert call_kwargs["intervention_date"] == "2024-01-20"
            assert call_kwargs["dependent_variable"] == "sales"


class TestModelsFactory:
    """Tests for factory functions."""

    def test_create_models_manager_from_config_dict(self):
        """Test creating manager from config dict."""
        register_model_adapter("mock", MockModel)

        try:
            config = {
                "MODEL": "mock",
                "PARAMS": {"INTERVENTION_DATE": "2024-01-15"},
            }

            manager = create_models_manager_from_config(config)

            assert isinstance(manager, ModelsManager)
            assert isinstance(manager.model, MockModel)
        finally:
            del MODEL_ADAPTERS["mock"]

    def test_create_models_manager_from_file(self):
        """Test creating manager from config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            products_path = str(Path(tmpdir) / "products.csv")
            pd.DataFrame({"product_id": ["p1"]}).to_csv(products_path, index=False)

            config = {
                "DATA": {
                    "TYPE": "simulator",
                    "PATH": products_path,
                    "START_DATE": "2024-01-01",
                    "END_DATE": "2024-01-31",
                },
                "MEASUREMENT": {
                    "MODEL": "interrupted_time_series",
                    "PARAMS": {
                        "INTERVENTION_DATE": "2024-01-15",
                    },
                },
            }
            config_path = str(Path(tmpdir) / "config.json")
            with open(config_path, "w") as f:
                json.dump(config, f)

            manager = create_models_manager(config_path)

            assert isinstance(manager, ModelsManager)
            assert manager.measurement_config == config["MEASUREMENT"]

    def test_create_models_manager_unknown_type(self):
        """Test creating manager with unknown model type."""
        config = {
            "MODEL": "unknown_model",
            "PARAMS": {"INTERVENTION_DATE": "2024-01-15"},
        }

        with pytest.raises(ValueError, match="Unknown model type"):
            create_models_manager_from_config(config)

    def test_register_invalid_model(self):
        """Test registering invalid model class."""

        class InvalidModel:
            pass

        with pytest.raises(ValueError, match="must implement Model"):
            register_model_adapter("invalid", InvalidModel)


class TestModelsManagerConnectionFailure:
    """Tests for connection failure handling."""

    def test_connection_failure_raises_error(self):
        """Test that connection failure raises ConnectionError."""
        mock_model = Mock(spec=Model)
        mock_model.connect.return_value = False

        config = {"PARAMS": {"INTERVENTION_DATE": "2024-01-15"}}

        with pytest.raises(ConnectionError, match="Failed to connect"):
            ModelsManager(config, mock_model)
