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
                "DATA": {
                    "TYPE": "simulator",
                    "MODE": "rule",
                    "SEED": 42,
                    "START_DATE": "2024-01-01",
                    "END_DATE": "2024-01-31"
                },
                "MEASUREMENT": {
                    "MODEL": "interrupted_time_series",
                    "PARAMS": {
                        "DEPENDENT_VARIABLE": "revenue",
                        "INTERVENTION_DATE": "2024-01-15",
                        "START_DATE": "2024-01-01",
                        "END_DATE": "2024-01-31"
                    }
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Create a DataFrame with product characteristics
                products_df = pd.DataFrame({
                    'product_id': ['product_1', 'product_2'],
                    'name': ['Product 1', 'Product 2'],
                    'category': ['Electronics', 'Electronics'],
                    'price': [99.99, 149.99]
                })
                
                # Call evaluate_impact with modeling integration
                result_path = evaluate_impact(
                    config_path=config_path,
                    products=products_df,
                    storage_url=tmpdir
                )
                
                # Verify result URL format
                assert result_path.startswith("file://")
                assert result_path.endswith('.json')
                
                # Load result data using storage backend to verify it exists
                from artefact_store import create_artefact_store
                storage = create_artefact_store(tmpdir)
                result_data = storage.load_json("results/impact_results.json", "default")
                
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
                "DATA": {
                    "TYPE": "simulator",
                    "MODE": "rule",
                    "SEED": 42,
                    "START_DATE": "2024-01-01",
                    "END_DATE": "2024-01-31"
                },
                "MEASUREMENT": {
                    "MODEL": "interrupted_time_series",
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
            with tempfile.TemporaryDirectory() as tmpdir:
                # Create a DataFrame with product characteristics
                products_df = pd.DataFrame({
                    'product_id': ['product_1'],
                    'name': ['Product 1'],
                    'category': ['Electronics'],
                    'price': [99.99]
                })
                
                # Should raise ValueError for missing intervention_date
                with pytest.raises(ValueError, match="INTERVENTION_DATE must be specified"):
                    evaluate_impact(
                        config_path=config_path,
                        products=products_df,
                        storage_url=tmpdir
                    )
        finally:
            Path(config_path).unlink()
    
    def test_evaluate_impact_returns_model_results_path(self):
        """Test that evaluate_impact returns path to model results, not CSV."""
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
                    "MODEL": "interrupted_time_series",
                    "PARAMS": {
                        "DEPENDENT_VARIABLE": "revenue",
                        "INTERVENTION_DATE": "2024-01-15",
                        "START_DATE": "2024-01-01",
                        "END_DATE": "2024-01-31"
                    }
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Create a DataFrame with product characteristics
                products_df = pd.DataFrame({
                    'product_id': ['product_1'],
                    'name': ['Product 1'],
                    'category': ['Electronics'],
                    'price': [99.99]
                })
                
                result_path = evaluate_impact(
                    config_path=config_path,
                    products=products_df,
                    storage_url=tmpdir
                )
                
                # Verify result is a JSON file (model results), not CSV
                assert result_path.endswith('.json')
                assert not result_path.endswith('.csv')
                
                # Verify it's the impact_results.json file from the model
                assert 'impact_results.json' in result_path
                
        finally:
            Path(config_path).unlink()
    
    def test_evaluate_impact_with_dataframe_products(self):
        """Test that evaluate_impact works with DataFrame input for products."""
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
                    "MODEL": "interrupted_time_series",
                    "PARAMS": {
                        "DEPENDENT_VARIABLE": "revenue",
                        "INTERVENTION_DATE": "2024-01-15",
                        "START_DATE": "2024-01-01",
                        "END_DATE": "2024-01-31"
                    }
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Create a DataFrame with product characteristics
                products_df = pd.DataFrame({
                    'product_id': ['prod_001', 'prod_002', 'prod_003'],
                    'name': ['Widget A', 'Widget B', 'Widget C'],
                    'category': ['Electronics', 'Electronics', 'Home'],
                    'price': [99.99, 149.99, 79.99]
                })
                
                result_path = evaluate_impact(
                    config_path=config_path,
                    products=products_df,
                    storage_url=tmpdir
                )
                
                # Verify result URL format
                assert result_path.startswith("file://")
                assert result_path.endswith('.json')
                
                # Load result data using storage backend to verify it exists
                from artefact_store import create_artefact_store
                storage = create_artefact_store(tmpdir)
                result_data = storage.load_json("results/impact_results.json", "default")
                
                # Verify model output structure
                assert result_data["model_type"] == "interrupted_time_series"
                assert result_data["intervention_date"] == "2024-01-15"
                assert result_data["dependent_variable"] == "revenue"
                assert "impact_estimates" in result_data
                assert "model_summary" in result_data
                
        finally:
            Path(config_path).unlink()
