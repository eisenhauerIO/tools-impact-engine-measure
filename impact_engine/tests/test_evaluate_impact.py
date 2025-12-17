"""Tests for evaluate_impact function with modeling layer integration."""

import pytest
import pandas as pd
import tempfile
import json
from pathlib import Path

from impact_engine import evaluate_impact


class TestEvaluateImpactIntegration:
    """Tests for evaluate_impact function with modeling layer integration."""
    
    def test_evaluate_impact_with_modeling_integration(self):
        """Test that evaluate_impact integrates data and modeling layers."""
        # Create a temporary configuration file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "data_source": {
                    "type": "simulator",
                    "connection": {"mode": "rule"}
                },
                "model": {
                    "type": "interrupted_time_series",
                    "parameters": {
                        "intervention_date": "2024-01-15",
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
            with tempfile.TemporaryDirectory() as tmpdir:
                # Call evaluate_impact with modeling integration
                result_path = evaluate_impact(
                    config_path=config_path,
                    products=["product_1", "product_2"],
                    output_path=tmpdir
                )
                
                # Verify result file exists
                assert Path(result_path).exists()
                assert result_path.endswith('.json')
                
                # Verify result file contains valid JSON with model results
                with open(result_path, 'r') as f:
                    result_data = json.load(f)
                
                # Verify model output structure
                assert result_data["model_type"] == "interrupted_time_series"
                assert result_data["intervention_date"] == "2024-01-15"
                assert result_data["dependent_variable"] == "revenue"
                assert "impact_estimates" in result_data
                assert "model_summary" in result_data
                
                # Verify impact estimates contain required fields
                impact_estimates = result_data["impact_estimates"]
                assert "intervention_effect" in impact_estimates
                assert "pre_intervention_mean" in impact_estimates
                assert "post_intervention_mean" in impact_estimates
                
        finally:
            Path(config_path).unlink()
    
    def test_evaluate_impact_missing_intervention_date(self):
        """Test that evaluate_impact raises error when intervention_date is missing."""
        # Create a configuration without intervention_date
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "data_source": {
                    "type": "simulator",
                    "connection": {"mode": "rule"}
                },
                "model": {
                    "type": "interrupted_time_series",
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
            with tempfile.TemporaryDirectory() as tmpdir:
                # Should raise ValueError for missing intervention_date
                with pytest.raises(ValueError, match="intervention_date must be specified"):
                    evaluate_impact(
                        config_path=config_path,
                        products=["product_1"],
                        output_path=tmpdir
                    )
        finally:
            Path(config_path).unlink()
    
    def test_evaluate_impact_returns_model_results_path(self):
        """Test that evaluate_impact returns path to model results, not CSV."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "data_source": {
                    "type": "simulator",
                    "connection": {"mode": "rule"}
                },
                "model": {
                    "type": "interrupted_time_series",
                    "parameters": {
                        "intervention_date": "2024-01-15",
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
            with tempfile.TemporaryDirectory() as tmpdir:
                result_path = evaluate_impact(
                    config_path=config_path,
                    products=["product_1"],
                    output_path=tmpdir
                )
                
                # Verify result is a JSON file (model results), not CSV
                assert result_path.endswith('.json')
                assert not result_path.endswith('.csv')
                
                # Verify it's the impact_results.json file from the model
                assert 'impact_results.json' in result_path
                
        finally:
            Path(config_path).unlink()
