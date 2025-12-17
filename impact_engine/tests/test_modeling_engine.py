"""Tests for ModelingEngine."""

import pytest
import pandas as pd
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock

from impact_engine.modeling import ModelingEngine, ModelInterface
from impact_engine.config import ConfigurationError


class MockModel(ModelInterface):
    """Mock model for testing."""
    
    def fit(self, data: pd.DataFrame, intervention_date: str, output_path: str, **kwargs) -> str:
        """Mock fit method."""
        result_file = Path(output_path) / "mock_results.json"
        result_file.parent.mkdir(parents=True, exist_ok=True)
        
        result_data = {
            "model_type": "mock",
            "intervention_date": intervention_date,
            "rows_processed": len(data)
        }
        
        with open(result_file, 'w') as f:
            json.dump(result_data, f)
        
        return str(result_file)
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """Mock validate_data method."""
        return not data.empty and 'date' in data.columns
    
    def get_required_columns(self) -> list:
        """Mock get_required_columns method."""
        return ['date', 'value']


class TestModelingEngineRegistration:
    """Tests for model registration functionality."""
    
    def test_register_model_success(self):
        """Test successful model registration."""
        engine = ModelingEngine()
        engine.register_model("mock", MockModel)
        
        assert "mock" in engine.get_available_models()
        assert engine.model_registry["mock"] == MockModel
    
    def test_register_model_invalid_class(self):
        """Test registration with invalid model class."""
        engine = ModelingEngine()
        
        class InvalidModel:
            pass
        
        with pytest.raises(ValueError, match="must implement ModelInterface"):
            engine.register_model("invalid", InvalidModel)
    
    def test_get_available_models(self):
        """Test getting list of available models."""
        engine = ModelingEngine()
        engine.register_model("mock1", MockModel)
        engine.register_model("mock2", MockModel)
        
        available = engine.get_available_models()
        assert "mock1" in available
        assert "mock2" in available
        assert len(available) == 2


class TestModelingEngineConfiguration:
    """Tests for configuration loading."""
    
    def test_load_config_success(self):
        """Test successful configuration loading."""
        engine = ModelingEngine()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "data_source": {
                    "type": "simulator",
                    "connection": {"mode": "rule"}
                },
                "model": {
                    "type": "mock",
                    "parameters": {
                        "dependent_variable": "revenue"
                    },
                    "time_range": {
                        "start_date": "2024-01-01",
                        "end_date": "2024-01-31"
                    }
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            loaded_config = engine.load_config(config_path)
            assert loaded_config["model"]["type"] == "mock"
            assert engine.current_config is not None
        finally:
            Path(config_path).unlink()
    
    def test_load_config_file_not_found(self):
        """Test loading non-existent configuration file."""
        engine = ModelingEngine()
        
        with pytest.raises(FileNotFoundError):
            engine.load_config("/nonexistent/path/config.json")
    
    def test_get_current_config(self):
        """Test getting current configuration."""
        engine = ModelingEngine()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "data_source": {
                    "type": "simulator",
                    "connection": {"mode": "rule"}
                },
                "model": {
                    "type": "mock",
                    "time_range": {
                        "start_date": "2024-01-01",
                        "end_date": "2024-01-31"
                    }
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            engine.load_config(config_path)
            current = engine.get_current_config()
            assert current is not None
            assert current["model"]["type"] == "mock"
        finally:
            Path(config_path).unlink()


class TestModelingEngineGetModel:
    """Tests for model retrieval."""
    
    def test_get_model_by_type(self):
        """Test getting model by explicit type."""
        engine = ModelingEngine()
        engine.register_model("mock", MockModel)
        
        model = engine.get_model("mock")
        assert isinstance(model, MockModel)
    
    def test_get_model_from_config(self):
        """Test getting model from loaded configuration."""
        engine = ModelingEngine()
        engine.register_model("mock", MockModel)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "data_source": {
                    "type": "simulator",
                    "connection": {"mode": "rule"}
                },
                "model": {
                    "type": "mock",
                    "time_range": {
                        "start_date": "2024-01-01",
                        "end_date": "2024-01-31"
                    }
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            engine.load_config(config_path)
            model = engine.get_model()
            assert isinstance(model, MockModel)
        finally:
            Path(config_path).unlink()
    
    def test_get_model_unknown_type(self):
        """Test getting unknown model type."""
        engine = ModelingEngine()
        
        with pytest.raises(ValueError, match="Unknown model type"):
            engine.get_model("unknown")
    
    def test_get_model_no_config(self):
        """Test getting model without configuration."""
        engine = ModelingEngine()
        engine.register_model("mock", MockModel)
        
        with pytest.raises(ConfigurationError, match="No configuration loaded"):
            engine.get_model()


class TestModelingEngineFitModel:
    """Tests for model fitting functionality."""
    
    def test_fit_model_success(self):
        """Test successful model fitting."""
        engine = ModelingEngine()
        engine.register_model("mock", MockModel)
        
        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'value': range(10)
        })
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result_path = engine.fit_model(
                data=data,
                intervention_date="2024-01-05",
                output_path=tmpdir,
                model_type="mock"
            )
            
            assert Path(result_path).exists()
            assert result_path.endswith('.json')
    
    def test_fit_model_empty_data(self):
        """Test fitting with empty data."""
        engine = ModelingEngine()
        engine.register_model("mock", MockModel)
        
        data = pd.DataFrame()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="Input data cannot be empty"):
                engine.fit_model(
                    data=data,
                    intervention_date="2024-01-05",
                    output_path=tmpdir,
                    model_type="mock"
                )
    
    def test_fit_model_invalid_data(self):
        """Test fitting with invalid data."""
        engine = ModelingEngine()
        engine.register_model("mock", MockModel)
        
        # Data missing required 'date' column
        data = pd.DataFrame({'value': range(10)})
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="Data validation failed"):
                engine.fit_model(
                    data=data,
                    intervention_date="2024-01-05",
                    output_path=tmpdir,
                    model_type="mock"
                )
    
    def test_fit_model_from_config(self):
        """Test fitting model using configuration."""
        engine = ModelingEngine()
        engine.register_model("mock", MockModel)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "data_source": {
                    "type": "simulator",
                    "connection": {"mode": "rule"}
                },
                "model": {
                    "type": "mock",
                    "time_range": {
                        "start_date": "2024-01-01",
                        "end_date": "2024-01-31"
                    }
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            engine.load_config(config_path)
            
            data = pd.DataFrame({
                'date': pd.date_range('2024-01-01', periods=10),
                'value': range(10)
            })
            
            with tempfile.TemporaryDirectory() as tmpdir:
                result_path = engine.fit_model(
                    data=data,
                    intervention_date="2024-01-05",
                    output_path=tmpdir
                )
                
                assert Path(result_path).exists()
        finally:
            Path(config_path).unlink()


class TestModelingEngineStatistics:
    """Tests for operation statistics tracking."""
    
    def test_operation_stats_initialization(self):
        """Test that operation stats are initialized."""
        engine = ModelingEngine()
        stats = engine.get_operation_stats()
        
        assert stats['config_loads'] == 0
        assert stats['model_fits'] == 0
        assert stats['model_instantiations'] == 0
        assert stats['total_fit_time'] == 0.0
        assert stats['failed_operations'] == 0
    
    def test_operation_stats_tracking(self):
        """Test that operation stats are tracked."""
        engine = ModelingEngine()
        engine.register_model("mock", MockModel)
        
        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'value': range(10)
        })
        
        with tempfile.TemporaryDirectory() as tmpdir:
            engine.fit_model(
                data=data,
                intervention_date="2024-01-05",
                output_path=tmpdir,
                model_type="mock"
            )
        
        stats = engine.get_operation_stats()
        assert stats['model_fits'] == 1
        assert stats['model_instantiations'] == 1
    
    def test_reset_stats(self):
        """Test resetting operation statistics."""
        engine = ModelingEngine()
        engine.register_model("mock", MockModel)
        
        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'value': range(10)
        })
        
        with tempfile.TemporaryDirectory() as tmpdir:
            engine.fit_model(
                data=data,
                intervention_date="2024-01-05",
                output_path=tmpdir,
                model_type="mock"
            )
        
        engine.reset_stats()
        stats = engine.get_operation_stats()
        
        assert stats['model_fits'] == 0
        assert stats['model_instantiations'] == 0


class TestInterruptedTimeSeriesModel:
    """Tests for InterruptedTimeSeriesModel result saving functionality."""
    
    def test_its_model_result_file_creation(self):
        """Test that ITS model creates result file at specified path."""
        from impact_engine.modeling import InterruptedTimeSeriesModel
        
        model = InterruptedTimeSeriesModel()
        
        # Create sample time series data
        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=30),
            'revenue': [1000 + i * 10 for i in range(30)]
        })
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result_path = model.fit(
                data=data,
                intervention_date="2024-01-15",
                output_path=tmpdir,
                dependent_variable="revenue"
            )
            
            # Verify result file exists
            assert Path(result_path).exists()
            assert result_path.endswith('.json')
    
    def test_its_model_result_file_content(self):
        """Test that ITS model saves valid JSON with required fields."""
        from impact_engine.modeling import InterruptedTimeSeriesModel
        
        model = InterruptedTimeSeriesModel()
        
        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=30),
            'revenue': [1000 + i * 10 for i in range(30)]
        })
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result_path = model.fit(
                data=data,
                intervention_date="2024-01-15",
                output_path=tmpdir,
                dependent_variable="revenue"
            )
            
            # Load and verify JSON content
            with open(result_path, 'r') as f:
                result_data = json.load(f)
            
            # Verify required fields
            assert result_data["model_type"] == "interrupted_time_series"
            assert result_data["intervention_date"] == "2024-01-15"
            assert result_data["dependent_variable"] == "revenue"
            assert "impact_estimates" in result_data
            assert "model_summary" in result_data
    
    def test_its_model_impact_estimates_structure(self):
        """Test that impact estimates have correct structure."""
        from impact_engine.modeling import InterruptedTimeSeriesModel
        
        model = InterruptedTimeSeriesModel()
        
        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=30),
            'revenue': [1000 + i * 10 for i in range(30)]
        })
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result_path = model.fit(
                data=data,
                intervention_date="2024-01-15",
                output_path=tmpdir,
                dependent_variable="revenue"
            )
            
            with open(result_path, 'r') as f:
                result_data = json.load(f)
            
            impact_estimates = result_data["impact_estimates"]
            
            # Verify impact estimate fields
            assert "intervention_effect" in impact_estimates
            assert "pre_intervention_mean" in impact_estimates
            assert "post_intervention_mean" in impact_estimates
            assert "absolute_change" in impact_estimates
            assert "percent_change" in impact_estimates
            
            # Verify they are numeric
            assert isinstance(impact_estimates["intervention_effect"], (int, float))
            assert isinstance(impact_estimates["pre_intervention_mean"], (int, float))
            assert isinstance(impact_estimates["post_intervention_mean"], (int, float))
    
    def test_its_model_model_summary_structure(self):
        """Test that model summary has correct structure."""
        from impact_engine.modeling import InterruptedTimeSeriesModel
        
        model = InterruptedTimeSeriesModel()
        
        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=30),
            'revenue': [1000 + i * 10 for i in range(30)]
        })
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result_path = model.fit(
                data=data,
                intervention_date="2024-01-15",
                output_path=tmpdir,
                dependent_variable="revenue"
            )
            
            with open(result_path, 'r') as f:
                result_data = json.load(f)
            
            model_summary = result_data["model_summary"]
            
            # Verify model summary fields
            assert "n_observations" in model_summary
            assert "pre_period_length" in model_summary
            assert "post_period_length" in model_summary
            assert "aic" in model_summary
            assert "bic" in model_summary
            
            # Verify counts are correct
            assert model_summary["n_observations"] == 30
            assert model_summary["pre_period_length"] == 14  # 2024-01-01 to 2024-01-14
            assert model_summary["post_period_length"] == 16  # 2024-01-15 to 2024-01-30
    
    def test_its_model_returns_file_path(self):
        """Test that fit method returns the correct file path."""
        from impact_engine.modeling import InterruptedTimeSeriesModel
        
        model = InterruptedTimeSeriesModel()
        
        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=30),
            'revenue': [1000 + i * 10 for i in range(30)]
        })
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result_path = model.fit(
                data=data,
                intervention_date="2024-01-15",
                output_path=tmpdir,
                dependent_variable="revenue"
            )
            
            # Verify path is a string
            assert isinstance(result_path, str)
            
            # Verify path points to existing file
            assert Path(result_path).exists()
            assert Path(result_path).is_file()
            
            # Verify path is in the output directory
            assert tmpdir in result_path
