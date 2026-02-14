"""Integration test for metrics_approximation through evaluate_impact().

Tests the typical end-to-end usage pattern:
1. User provides products.csv
2. User provides config.yaml with DATA.ENRICHMENT section
3. User calls evaluate_impact(config.yaml)
4. Engine handles everything internally (adapter, enrichment, transform, model)
"""

from pathlib import Path

import pytest
import yaml

CONFIG_PATH = Path(__file__).parent / "fixtures" / "config_pipeline.yaml"


@pytest.fixture
def products_csv(tmp_path):
    """Create products.csv with basic product characteristics.

    Note: quality_score is NOT needed here - enrich() generates it internally.
    """
    from online_retail_simulator.simulate import simulate_products

    sim_config = {
        "STORAGE": {"PATH": str(tmp_path / "simulation")},
        "RULE": {
            "PRODUCTS": {
                "FUNCTION": "simulate_products_rule_based",
                "PARAMS": {"num_products": 5},
            },
        },
    }

    sim_config_path = tmp_path / "sim_config.yaml"
    with open(sim_config_path, "w") as f:
        yaml.dump(sim_config, f)

    job_info = simulate_products(str(sim_config_path))
    products = job_info.load_df("products")

    products_path = tmp_path / "products.csv"
    products.to_csv(products_path, index=False)

    return products_path


@pytest.fixture
def impact_config(tmp_path, products_csv):
    """Load config and update PATH to point to products.csv."""
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    config["DATA"]["SOURCE"]["CONFIG"]["path"] = str(products_csv)

    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    return config_path


class TestMetricsApproximationPipeline:
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
        import json

        from impact_engine_measure import evaluate_impact

        results_path = evaluate_impact(str(impact_config), str(tmp_path / "output"))

        with open(results_path) as f:
            results = json.load(f)

        assert results["model_type"] == "metrics_approximation"
        assert results["data"]["model_params"]["response_function"] == "linear"
        assert results["data"]["model_summary"]["n_products"] == 5
        assert results["data"]["impact_estimates"]["impact"] >= 0
