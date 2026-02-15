"""Tests for evaluate_impact function with modeling layer integration."""

import json
import os
import tempfile

import pandas as pd
import pytest

from impact_engine_measure import evaluate_impact


class TestEvaluateImpactIntegration:
    """Tests for evaluate_impact function with modeling layer integration."""

    def test_evaluate_impact_with_modeling_integration(self):
        """Test that evaluate_impact integrates data and modeling layers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create products CSV file
            products_df = pd.DataFrame(
                {
                    "product_id": ["product_1", "product_2"],
                    "name": ["Product 1", "Product 2"],
                    "category": ["Electronics", "Electronics"],
                    "price": [99.99, 149.99],
                }
            )
            products_path = os.path.join(tmpdir, "products.csv")
            products_df.to_csv(products_path, index=False)

            # Create a configuration file with new SOURCE/TRANSFORM structure
            config_path = os.path.join(tmpdir, "config.json")
            config = {
                "DATA": {
                    "SOURCE": {
                        "type": "simulator",
                        "CONFIG": {
                            "path": products_path,
                            "mode": "rule",
                            "seed": 42,
                            "start_date": "2024-01-01",
                            "end_date": "2024-01-31",
                        },
                    },
                    "TRANSFORM": {
                        "FUNCTION": "aggregate_by_date",
                        "PARAMS": {"metric": "revenue"},
                    },
                },
                "MEASUREMENT": {
                    "MODEL": "interrupted_time_series",
                    "PARAMS": {
                        "dependent_variable": "revenue",
                        "intervention_date": "2024-01-15",
                    },
                },
            }
            with open(config_path, "w") as f:
                json.dump(config, f)

            # Call evaluate_impact with modeling integration
            result_path = evaluate_impact(config_path=config_path, storage_url=tmpdir)

            # Verify result path format (now includes job ID)
            assert result_path.endswith(".json")
            assert "job-impact-engine-" in result_path  # Job ID prefix

            # Load result data directly from the returned path
            with open(result_path, "r") as f:
                result_data = json.load(f)

            # Verify stable envelope structure
            assert result_data["schema_version"] == "2.0"
            assert result_data["model_type"] == "interrupted_time_series"

            # Verify standardized three-key data structure
            data = result_data["data"]
            assert data["model_params"]["intervention_date"] == "2024-01-15"
            assert data["model_params"]["dependent_variable"] == "revenue"
            assert "impact_estimates" in data
            assert "model_summary" in data

            # Verify impact estimates contain required fields
            impact_estimates = data["impact_estimates"]
            assert "intervention_effect" in impact_estimates
            assert "pre_intervention_mean" in impact_estimates
            assert "post_intervention_mean" in impact_estimates

    def test_evaluate_impact_missing_intervention_date(self):
        """Test that evaluate_impact raises error when intervention_date is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create products CSV file
            products_df = pd.DataFrame(
                {
                    "product_id": ["product_1"],
                    "name": ["Product 1"],
                    "category": ["Electronics"],
                    "price": [99.99],
                }
            )
            products_path = os.path.join(tmpdir, "products.csv")
            products_df.to_csv(products_path, index=False)

            # Create a configuration without intervention_date
            config_path = os.path.join(tmpdir, "config.json")
            config = {
                "DATA": {
                    "SOURCE": {
                        "type": "simulator",
                        "CONFIG": {
                            "path": products_path,
                            "mode": "rule",
                            "seed": 42,
                            "start_date": "2024-01-01",
                            "end_date": "2024-01-31",
                        },
                    },
                    "TRANSFORM": {
                        "FUNCTION": "aggregate_by_date",
                        "PARAMS": {"metric": "revenue"},
                    },
                },
                "MEASUREMENT": {
                    "MODEL": "interrupted_time_series",
                    "PARAMS": {
                        "dependent_variable": "revenue",
                        # No intervention_date - should fail
                    },
                },
            }
            with open(config_path, "w") as f:
                json.dump(config, f)

            # Should raise ValueError for missing intervention_date (validated by model)
            with pytest.raises(ValueError, match="intervention_date"):
                evaluate_impact(config_path=config_path, storage_url=tmpdir)

    def test_evaluate_impact_returns_model_results_path(self):
        """Test that evaluate_impact returns path to model results, not CSV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create products CSV file
            products_df = pd.DataFrame(
                {
                    "product_id": ["product_1"],
                    "name": ["Product 1"],
                    "category": ["Electronics"],
                    "price": [99.99],
                }
            )
            products_path = os.path.join(tmpdir, "products.csv")
            products_df.to_csv(products_path, index=False)

            # Create configuration file with new structure
            config_path = os.path.join(tmpdir, "config.json")
            config = {
                "DATA": {
                    "SOURCE": {
                        "type": "simulator",
                        "CONFIG": {
                            "path": products_path,
                            "mode": "rule",
                            "seed": 42,
                            "start_date": "2024-01-01",
                            "end_date": "2024-01-31",
                        },
                    },
                    "TRANSFORM": {
                        "FUNCTION": "aggregate_by_date",
                        "PARAMS": {"metric": "revenue"},
                    },
                },
                "MEASUREMENT": {
                    "MODEL": "interrupted_time_series",
                    "PARAMS": {
                        "dependent_variable": "revenue",
                        "intervention_date": "2024-01-15",
                    },
                },
            }
            with open(config_path, "w") as f:
                json.dump(config, f)

            result_path = evaluate_impact(config_path=config_path, storage_url=tmpdir)

            # Verify result is a JSON file (model results), not CSV
            assert result_path.endswith(".json")
            assert not result_path.endswith(".csv")

            # Verify it's the impact_results.json file from the model
            assert "impact_results.json" in result_path

    def test_evaluate_impact_with_multiple_products(self):
        """Test that evaluate_impact works with multiple products."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create products CSV file with multiple products
            products_df = pd.DataFrame(
                {
                    "product_id": ["prod_001", "prod_002", "prod_003"],
                    "name": ["Widget A", "Widget B", "Widget C"],
                    "category": ["Electronics", "Electronics", "Home"],
                    "price": [99.99, 149.99, 79.99],
                }
            )
            products_path = os.path.join(tmpdir, "products.csv")
            products_df.to_csv(products_path, index=False)

            # Create configuration file with new structure
            config_path = os.path.join(tmpdir, "config.json")
            config = {
                "DATA": {
                    "SOURCE": {
                        "type": "simulator",
                        "CONFIG": {
                            "path": products_path,
                            "mode": "rule",
                            "seed": 42,
                            "start_date": "2024-01-01",
                            "end_date": "2024-01-31",
                        },
                    },
                    "TRANSFORM": {
                        "FUNCTION": "aggregate_by_date",
                        "PARAMS": {"metric": "revenue"},
                    },
                },
                "MEASUREMENT": {
                    "MODEL": "interrupted_time_series",
                    "PARAMS": {
                        "dependent_variable": "revenue",
                        "intervention_date": "2024-01-15",
                    },
                },
            }
            with open(config_path, "w") as f:
                json.dump(config, f)

            result_path = evaluate_impact(config_path=config_path, storage_url=tmpdir)

            # Verify result path format (now includes job ID)
            assert result_path.endswith(".json")
            assert "job-impact-engine-" in result_path  # Job ID prefix

            # Load result data directly from the returned path
            with open(result_path, "r") as f:
                result_data = json.load(f)

            # Verify stable envelope structure
            assert result_data["schema_version"] == "2.0"
            assert result_data["model_type"] == "interrupted_time_series"

            # Verify standardized data structure
            data = result_data["data"]
            assert data["model_params"]["intervention_date"] == "2024-01-15"
            assert data["model_params"]["dependent_variable"] == "revenue"
            assert "impact_estimates" in data
            assert "model_summary" in data
