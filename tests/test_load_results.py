"""Tests for load_results() and MeasureJobResult."""

import json
import tempfile

import pandas as pd
import pytest
from artifact_store import create_job

from impact_engine_measure import MeasureJobResult, evaluate_impact, load_results
from impact_engine_measure.models.base import SCHEMA_VERSION


class TestLoadResultsRoundTrip:
    """Round-trip: evaluate_impact() -> load_results()."""

    def test_round_trip(self):
        """Run a full pipeline then load results back; verify all fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            products_df = pd.DataFrame(
                {
                    "product_id": ["product_1", "product_2"],
                    "name": ["Product 1", "Product 2"],
                    "category": ["Electronics", "Electronics"],
                    "price": [99.99, 149.99],
                }
            )
            products_path = f"{tmpdir}/products.csv"
            products_df.to_csv(products_path, index=False)

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
            config_path = f"{tmpdir}/config.json"
            with open(config_path, "w") as f:
                json.dump(config, f)

            job_info = evaluate_impact(config_path=config_path, storage_url=tmpdir)
            result = load_results(job_info)

            assert isinstance(result, MeasureJobResult)
            assert result.job_id == job_info.job_id
            assert result.schema_version == SCHEMA_VERSION
            assert result.model_type == "interrupted_time_series"
            assert result.created_at  # non-empty

            # Config round-trip
            assert result.config["DATA"]["TRANSFORM"]["FUNCTION"] == "aggregate_by_date"

            # Impact results envelope
            assert result.impact_results["schema_version"] == SCHEMA_VERSION
            assert "impact_estimates" in result.impact_results["data"]

            # DataFrames loaded
            assert isinstance(result.products, pd.DataFrame)
            assert not result.products.empty
            assert isinstance(result.business_metrics, pd.DataFrame)
            assert not result.business_metrics.empty
            assert isinstance(result.transformed_metrics, pd.DataFrame)
            assert not result.transformed_metrics.empty


class TestLoadResultsSynthetic:
    """Fast tests using hand-written manifests (no pipeline run)."""

    @pytest.fixture
    def synthetic_job(self, tmp_path):
        """Create a minimal job directory with all required artifacts."""
        job = create_job(str(tmp_path), prefix="test-job", job_id="synth-001")
        store = job.get_store()

        products = pd.DataFrame({"product_id": ["p1"], "price": [10.0]})
        metrics = pd.DataFrame({"date": ["2024-01-01"], "revenue": [100.0]})
        artifact = pd.DataFrame({"product_id": ["p1"], "fitted": [99.0]})

        store.write_parquet("products.parquet", products)
        store.write_parquet("business_metrics.parquet", metrics)
        store.write_parquet("transformed_metrics.parquet", metrics)
        store.write_json(
            "impact_results.json",
            {
                "schema_version": SCHEMA_VERSION,
                "model_type": "test_model",
                "data": {"model_params": {}, "impact_estimates": {}, "model_summary": {}},
                "metadata": {},
            },
        )
        store.write_yaml("config.yaml", {"DATA": {}, "MEASUREMENT": {}})
        store.write_parquet("test_model__detail.parquet", artifact)

        manifest = {
            "schema_version": SCHEMA_VERSION,
            "model_type": "test_model",
            "created_at": "2024-01-01T00:00:00+00:00",
            "files": {
                "config": {"path": "config.yaml", "format": "yaml"},
                "products": {"path": "products.parquet", "format": "parquet"},
                "business_metrics": {"path": "business_metrics.parquet", "format": "parquet"},
                "transformed_metrics": {
                    "path": "transformed_metrics.parquet",
                    "format": "parquet",
                },
                "impact_results": {"path": "impact_results.json", "format": "json"},
                "test_model__detail": {
                    "path": "test_model__detail.parquet",
                    "format": "parquet",
                },
            },
        }
        store.write_json("manifest.json", manifest)

        return job

    def test_loads_all_fields(self, synthetic_job):
        result = load_results(synthetic_job)

        assert result.job_id == synthetic_job.job_id
        assert result.schema_version == SCHEMA_VERSION
        assert result.model_type == "test_model"
        assert result.created_at == "2024-01-01T00:00:00+00:00"
        assert isinstance(result.config, dict)
        assert isinstance(result.impact_results, dict)
        assert isinstance(result.products, pd.DataFrame)
        assert isinstance(result.business_metrics, pd.DataFrame)
        assert isinstance(result.transformed_metrics, pd.DataFrame)

    def test_model_artifact_prefix_stripped(self, synthetic_job):
        result = load_results(synthetic_job)

        assert "detail" in result.model_artifacts
        assert "test_model__detail" not in result.model_artifacts
        assert isinstance(result.model_artifacts["detail"], pd.DataFrame)
        assert list(result.model_artifacts["detail"].columns) == ["product_id", "fitted"]


class TestLoadResultsErrors:
    """Error handling."""

    def test_missing_manifest(self, tmp_path):
        job = create_job(str(tmp_path), prefix="test-job", job_id="no-manifest")
        with pytest.raises(FileNotFoundError, match="manifest.json"):
            load_results(job)

    def test_incompatible_schema_version(self, tmp_path):
        job = create_job(str(tmp_path), prefix="test-job", job_id="bad-version")
        store = job.get_store()
        store.write_json(
            "manifest.json",
            {
                "schema_version": "99.0",
                "model_type": "test",
                "created_at": "",
                "files": {},
            },
        )
        with pytest.raises(ValueError, match="Incompatible schema version"):
            load_results(job)
