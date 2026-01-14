"""Integration tests for metrics approximation pipeline with evaluate_impact().

Tests the typical usage pattern:
1. User provides products.csv
2. User provides config.yaml with DATA.ENRICHMENT section
3. User calls evaluate_impact(config.yaml)
4. Engine handles everything internally (adapter, enrichment, transform, model)
"""

from pathlib import Path

import pytest
import yaml


CONFIG_PATH = Path(__file__).parent / "fixtures" / "config_metrics_approximation_pipeline.yaml"


@pytest.fixture
def products_csv(tmp_path):
    """Create products.csv with basic product characteristics.

    Note: quality_score is NOT needed here - enrich() generates it internally.
    """
    try:
        from online_retail_simulator.simulate import simulate_characteristics
    except ImportError:
        pytest.skip("online_retail_simulator not available")

    sim_config = {
        "STORAGE": {"PATH": str(tmp_path / "simulation")},
        "RULE": {
            "CHARACTERISTICS": {
                "FUNCTION": "simulate_characteristics_rule_based",
                "PARAMS": {"num_products": 5},
            },
        },
    }

    sim_config_path = tmp_path / "sim_config.yaml"
    with open(sim_config_path, "w") as f:
        yaml.dump(sim_config, f)

    job_info = simulate_characteristics(str(sim_config_path))
    products = job_info.load_df("products")

    products_path = tmp_path / "products.csv"
    products.to_csv(products_path, index=False)

    return products_path


@pytest.fixture
def impact_config(tmp_path, products_csv):
    """Load config and update PATH to point to products.csv."""
    # Read the config file
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    # Update PATH to point to the generated products.csv
    config["DATA"]["SOURCE"]["CONFIG"]["PATH"] = str(products_csv)

    # Write updated config to tmp_path
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    return config_path


class TestRealCatalogSimulatorPipeline:
    """Integration tests using evaluate_impact() with unified config."""

    def test_full_pipeline_via_evaluate_impact(self, impact_config, tmp_path):
        """
        End-to-end test using evaluate_impact() with a single unified config.

        This is the typical usage pattern - single call does everything:
        - Engine creates CatalogSimulatorAdapter
        - Adapter handles enrichment internally
        - Transform extracts quality_before/quality_after
        - MetricsApproximationAdapter computes impact
        """
        from impact_engine import evaluate_impact

        # Single call to evaluate_impact() - engine handles everything
        results = evaluate_impact(str(impact_config), str(tmp_path / "output"))

        # Verify results
        assert results["model_type"] == "metrics_approximation"
        assert results["response_function"] == "linear"
        assert results["impact_estimates"]["n_products"] == 5
        assert results["impact_estimates"]["total_approximated_impact"] >= 0
