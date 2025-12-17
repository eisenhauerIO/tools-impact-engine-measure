"""Tests for ModelsManager."""

import pytest
import pandas as pd
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock

from impact_engine.models import ModelsManager, Model
from impact_engine.config import ConfigurationError


class MockModel(Model):
    """Mock model for testing."""
    
    def __init__(self):
        self.is_connected = False
        self.config = None
        self.storage = None
        self.tenant_id = "default"
    
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
        return {
            'data': data,
            'intervention_date': intervention_date,
            'kwargs': kwargs
        }
    
    def transform_inbound(self, model_results):
        """Mock transform_inbound method."""
        return {
            'model_type': 'mock',
            'results': model_results
        }
    
    def fit(self, data: pd.DataFrame, intervention_date: str, output_path: str, **kwargs) -> str:
        """Mock fit method."""
        if not self.is_connected:
            raise ConnectionError("Model not connected. Call connect() first.")
        
        if not self.storage:
            raise ValueError("Storage backend is required but not configured")
            
        result_data = {
            "model_type": "mock",
            "intervention_date": intervention_date,
            "rows_processed": len(data)
        }
        
        result_path = f"{output_path}/mock_results.json"
        stored_path = self.storage.store_json(result_path, result_data, self.tenant_id)
        
        return stored_path
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """Mock validate_data method."""
        return not data.empty and 'date' in data.columns
    
    def get_required_columns(self) -> list:
        """Mock get_required_columns method."""
        return ['date', 'value']


class TestModelsManagerRegistration:
    """Tests for model registration functionality."""
    
    def test_register_model_success(self):
        """Test successful model registration."""
        engine = ModelsManager()
        engine.register_model("mock", MockModel)
        
        assert "mock" in engine.get_available_models()
        assert engine.model_registry["mock"] == MockModel
    
    def test_register_model_invalid_class(self):
        """Test registration with invalid model class."""
        engine = ModelsManager()
        
        class InvalidModel:
            pass
        
        with pytest.raises(ValueError, match="must implement Model"):
            engine.register_model("invalid", InvalidModel)
    
    def test_get_available_models(self):
        """Test getting list of available models."""
        engine = ModelsManager()
        engine.register_model("mock1", MockModel)
        engine.register_model("mock2", MockModel)
        
        available = engine.get_available_models()
        assert "mock1" in available
        assert "mock2" in available
        assert "interrupted_time_series" in available  # Built-in model
        assert len(available) == 3


class TestModelsManagerConfiguration:
    """Tests for configuration loading."""
    
    def test_load_config_success(self):
        """Test successful configuration loading from file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "DATA": {
                    "TYPE": "simulator",
                    "MODE": "rule",
                    "SEED": 42,
                    "START_DATE": "2024-01-01",
                    "END_DATE": "2024-01-31"
                },
                "MEASUREMENT": {
                    "MODEL": "mock",
                    "PARAMS": {
                        "DEPENDENT_VARIABLE": "revenue",
                        "START_DATE": "2024-01-01",
                        "END_DATE": "2024-01-31"
                    }
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            engine = ModelsManager.from_config_file(config_path)
            assert engine.measurement_config["MODEL"] == "mock"
        finally:
            Path(config_path).unlink()
    
    def test_load_config_file_not_found(self):
        """Test loading non-existent configuration file."""
        with pytest.raises(FileNotFoundError):
            ModelsManager.from_config_file("/nonexistent/path/config.json")
    
    def test_get_current_config(self):
        """Test getting current configuration."""
        engine = ModelsManager()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "DATA": {
                    "TYPE": "simulator",
                    "MODE": "rule",
                    "SEED": 42,
                    "START_DATE": "2024-01-01",
                    "END_DATE": "2024-01-31"
                },
                "MEASUREMENT": {
                    "MODEL": "mock",
                    "PARAMS": {
                        "START_DATE": "2024-01-01",
                        "END_DATE": "2024-01-31"
                    }
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            engine = ModelsManager.from_config_file(config_path)
            assert engine.measurement_config is not None
            assert engine.measurement_config["MODEL"] == "mock"
        finally:
            Path(config_path).unlink()


class TestModelsManagerGetModel:
    """Tests for model retrieval."""
    
    def test_get_model_by_type(self):
        """Test getting model by explicit type."""
        engine = ModelsManager()
        engine.register_model("mock", MockModel)
        
        model = engine.get_model("mock")
        assert isinstance(model, MockModel)
    
    def test_get_model_from_config(self):
        """Test getting model from loaded configuration."""
        engine = ModelsManager()
        engine.register_model("mock", MockModel)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "DATA": {
                    "TYPE": "simulator",
                    "MODE": "rule",
                    "SEED": 42,
                    "START_DATE": "2024-01-01",
                    "END_DATE": "2024-01-31"
                },
                "MEASUREMENT": {
                    "MODEL": "mock",
                    "PARAMS": {
                        "START_DATE": "2024-01-01",
                        "END_DATE": "2024-01-31"
                    }
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            engine = ModelsManager.from_config_file(config_path)
            engine.register_model("mock", MockModel)
            model = engine.get_model()
            assert isinstance(model, MockModel)
        finally:
            Path(config_path).unlink()
    
    def test_get_model_unknown_type(self):
        """Test getting unknown model type."""
        engine = ModelsManager()
        
        with pytest.raises(ValueError, match="Unknown model type"):
            engine.get_model("unknown")
    
    def test_get_model_no_config(self):
        """Test getting model without specifying type and no config model."""
        # Create engine with minimal config that doesn't have the requested model
        measurement_config = {"MODEL": "nonexistent", "PARAMS": {}}
        engine = ModelsManager(measurement_config)
        engine.register_model("mock", MockModel)
        
        with pytest.raises(ValueError, match="Unknown model type"):
            engine.get_model()  # Will try to get "nonexistent" model from config


class TestModelsManagerFitModel:
    """Tests for model fitting functionality."""
    
    def test_fit_model_success(self):
        """Test successful model fitting."""
        from artefact_store import create_artefact_store
        
        engine = ModelsManager()
        engine.register_model("mock", MockModel)
        
        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'value': range(10)
        })
        
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = create_artefact_store(tmpdir)
            result_path = engine.fit_model(
                data=data,
                intervention_date="2024-01-05",
                output_path="results",
                model_type="mock",
                storage=storage,
                tenant_id="test_tenant"
            )
            
            assert result_path.startswith("file://")
            assert result_path.endswith('.json')
    
    def test_fit_model_empty_data(self):
        """Test fitting with empty data."""
        from artefact_store import create_artefact_store
        
        engine = ModelsManager()
        engine.register_model("mock", MockModel)
        
        data = pd.DataFrame()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = create_artefact_store(tmpdir)
            # Should work with empty data since MockModel handles it
            result = engine.fit_model(
                data=data,
                intervention_date="2024-01-05",
                output_path="results",
                model_type="mock",
                storage=storage,
                tenant_id="test_tenant"
            )
            assert result is not None
    
    def test_fit_model_invalid_data(self):
        """Test fitting with invalid data."""
        from artefact_store import create_artefact_store
        
        engine = ModelsManager()
        engine.register_model("mock", MockModel)
        
        # Data missing required 'date' column
        data = pd.DataFrame({'value': range(10)})
        
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = create_artefact_store(tmpdir)
            # Should work since MockModel handles any data
            result = engine.fit_model(
                data=data,
                intervention_date="2024-01-05",
                output_path="results",
                model_type="mock",
                storage=storage,
                tenant_id="test_tenant"
            )
            assert result is not None
    
    def test_fit_model_from_config(self):
        """Test fitting model using configuration."""
        engine = ModelsManager()
        engine.register_model("mock", MockModel)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "DATA": {
                    "TYPE": "simulator",
                    "MODE": "rule",
                    "SEED": 42,
                    "START_DATE": "2024-01-01",
                    "END_DATE": "2024-01-31"
                },
                "MEASUREMENT": {
                    "MODEL": "mock",
                    "PARAMS": {
                        "START_DATE": "2024-01-01",
                        "END_DATE": "2024-01-31"
                    }
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            engine = ModelsManager.from_config_file(config_path)
            engine.register_model("mock", MockModel)
            
            data = pd.DataFrame({
                'date': pd.date_range('2024-01-01', periods=10),
                'value': range(10)
            })
            
            with tempfile.TemporaryDirectory() as tmpdir:
                from artefact_store import create_artefact_store
                storage = create_artefact_store(tmpdir)
                
                result_path = engine.fit_model(
                    data=data,
                    intervention_date="2024-01-05",
                    output_path="results",
                    storage=storage,
                    tenant_id="test_tenant"
                )
                
                assert result_path.startswith("file://")
        finally:
            Path(config_path).unlink()


class TestModelsManagerStatistics:
    """Tests for operation statistics tracking."""
    
    def test_operation_stats_initialization(self):
        """Test that simplified engine works without stats."""
        engine = ModelsManager()
        # Just verify engine works without stats
        assert len(engine.get_available_models()) > 0
    
    def test_operation_stats_tracking(self):
        """Test that engine works without stats tracking."""
        engine = ModelsManager()
        engine.register_model("mock", MockModel)
        
        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'value': range(10)
        })
        
        with tempfile.TemporaryDirectory() as tmpdir:
            from artefact_store import create_artefact_store
            storage = create_artefact_store(tmpdir)
            
            result = engine.fit_model(
                data=data,
                intervention_date="2024-01-05",
                output_path="results",
                model_type="mock",
                storage=storage,
                tenant_id="test_tenant"
            )
            assert result is not None
    
    def test_reset_stats(self):
        """Test that simplified engine works without reset stats."""
        engine = ModelsManager()
        # Just verify engine continues to work
        assert len(engine.get_available_models()) > 0


