"""Tests for CatalogSimulatorAdapter."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from artifact_store import create_job

from impact_engine.metrics.catalog_simulator import CatalogSimulatorAdapter


class TestCatalogSimulatorAdapter:
    """Tests for CatalogSimulatorAdapter functionality."""

    def test_connect_success(self):
        """Test successful adapter connection."""
        adapter = CatalogSimulatorAdapter()

        config = {"mode": "rule", "seed": 42}

        result = adapter.connect(config)
        assert result is True
        assert adapter.is_connected is True
        # Check that provided config values are stored (adapter may add additional fields)
        assert adapter.config["mode"] == config["mode"]
        assert adapter.config["seed"] == config["seed"]

    def test_connect_stores_config(self):
        """Test that connect stores provided config values."""
        adapter = CatalogSimulatorAdapter()

        result = adapter.connect({"mode": "rule", "seed": 42})
        assert result is True
        assert adapter.config["mode"] == "rule"
        assert adapter.config["seed"] == 42

    def test_validate_connection_success(self):
        """Test connection validation when connected and simulator available."""
        adapter = CatalogSimulatorAdapter()
        adapter.connect({"mode": "rule", "seed": 42})

        # Mock the core module with RuleBackend
        mock_core = MagicMock()
        with patch.dict("sys.modules", {"online_retail_simulator.core": mock_core}):
            assert adapter.validate_connection() is True

    def test_validate_connection_not_connected(self):
        """Test connection validation when not connected."""
        adapter = CatalogSimulatorAdapter()

        assert adapter.validate_connection() is False

    def test_validate_connection_simulator_not_available(self):
        """Test connection validation when simulator not available."""
        adapter = CatalogSimulatorAdapter()
        adapter.connect({"mode": "rule", "seed": 42})

        with patch("builtins.__import__", side_effect=ImportError):
            assert adapter.validate_connection() is False

    def test_transform_outbound_success(self):
        """Test successful outbound transformation."""
        adapter = CatalogSimulatorAdapter()
        adapter.connect({"mode": "rule", "seed": 42})

        products = pd.DataFrame(
            {
                "product_id": ["prod1", "prod2"],
                "name": ["Product 1", "Product 2"],
                "category": ["Electronics", "Books"],
                "price": [100.0, 50.0],
            }
        )

        result = adapter.transform_outbound(products, "2024-01-01", "2024-01-31")

        assert "product_characteristics" in result
        assert "rule_config" in result

        # Check product characteristics (should have product_identifier mapped from product_id)
        prod_chars = result["product_characteristics"]
        assert "product_identifier" in prod_chars.columns
        assert "name" in prod_chars.columns
        assert "category" in prod_chars.columns
        assert "price" in prod_chars.columns

        # Check rule config structure
        rule_config = result["rule_config"]
        assert "PRODUCTS" in rule_config
        assert "METRICS" in rule_config
        assert rule_config["METRICS"]["PARAMS"]["date_start"] == "2024-01-01"
        assert rule_config["METRICS"]["PARAMS"]["date_end"] == "2024-01-31"
        assert rule_config["METRICS"]["PARAMS"]["seed"] == 42

    def test_transform_outbound_missing_product_id(self):
        """Test outbound transformation with missing product_id column."""
        adapter = CatalogSimulatorAdapter()
        adapter.connect({"mode": "rule", "seed": 42})

        products = pd.DataFrame({"name": ["Product 1"], "category": ["Electronics"]})

        result = adapter.transform_outbound(products, "2024-01-01", "2024-01-31")

        # Should create product_identifier from index
        prod_chars = result["product_characteristics"]
        assert "product_identifier" in prod_chars.columns
        assert prod_chars["product_identifier"].iloc[0] == "0"

    def test_transform_outbound_missing_optional_columns(self):
        """Test outbound transformation with missing optional columns."""
        adapter = CatalogSimulatorAdapter()
        adapter.connect({"mode": "rule", "seed": 42})

        products = pd.DataFrame({"product_id": ["prod1"]})

        result = adapter.transform_outbound(products, "2024-01-01", "2024-01-31")

        prod_chars = result["product_characteristics"]
        assert "product_identifier" in prod_chars.columns
        assert prod_chars["product_identifier"].iloc[0] == "prod1"
        # Optional columns (name, category, price) are not fabricated

    def test_transform_inbound_success(self):
        """Test successful inbound transformation."""
        adapter = CatalogSimulatorAdapter()

        # Mock RuleBackend output (uses product_identifier and ordered_units)
        external_data = pd.DataFrame(
            {
                "product_identifier": ["prod1"],
                "name": ["Product 1"],
                "category": ["Electronics"],
                "price": [100.0],
                "date": ["2024-01-01"],
                "ordered_units": [5],
                "revenue": [500.0],
            }
        )

        result = adapter.transform_inbound(external_data)

        assert isinstance(result, pd.DataFrame)
        assert "product_id" in result.columns  # product_identifier mapped to product_id
        assert "sales_volume" in result.columns  # ordered_units mapped to sales_volume
        assert "revenue" in result.columns
        # Metadata (metrics_source, retrieval_timestamp) is now added by MetricsManager

        # Check that product_identifier was mapped to product_id
        assert result["product_id"].iloc[0] == "prod1"
        # Check that ordered_units was mapped to sales_volume
        assert result["sales_volume"].iloc[0] == 5

    def test_transform_inbound_invalid_input(self):
        """Test inbound transformation with invalid input."""
        adapter = CatalogSimulatorAdapter()

        with pytest.raises(ValueError, match="Expected pandas DataFrame"):
            adapter.transform_inbound("invalid_data")

    def test_transform_inbound_empty_dataframe(self):
        """Test inbound transformation with empty DataFrame."""
        adapter = CatalogSimulatorAdapter()

        result = adapter.transform_inbound(pd.DataFrame())

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
        # Should have standard columns
        expected_columns = [
            "product_id",
            "name",
            "category",
            "price",
            "date",
            "sales_volume",
            "revenue",
            "inventory_level",
            "customer_engagement",
            "metrics_source",
            "retrieval_timestamp",
        ]
        for col in expected_columns:
            assert col in result.columns

    def test_retrieve_business_metrics_success(self, tmp_path):
        """Test successful business metrics retrieval."""
        # Create a parent job for nested job creation
        parent_job = create_job(str(tmp_path), prefix="test-parent")

        adapter = CatalogSimulatorAdapter()
        adapter.connect({"mode": "rule", "seed": 42, "parent_job": parent_job})

        products = pd.DataFrame({"product_id": ["prod1"], "name": ["Product 1"]})

        # Mock simulate_metrics to save metrics.csv to the job
        def mock_simulate_metrics(job_info, config_path):
            # Simulate what the real function does: save metrics to job
            metrics_df = pd.DataFrame(
                {
                    "product_identifier": ["prod1"],
                    "name": ["Product 1"],
                    "category": ["Electronics"],
                    "price": [100.0],
                    "date": ["2024-01-01"],
                    "ordered_units": [5],
                    "revenue": [500.0],
                }
            )
            job_info.save_df("metrics", metrics_df)
            return job_info

        mock_simulate_module = MagicMock()
        mock_simulate_module.simulate_metrics = mock_simulate_metrics

        with patch.dict("sys.modules", {"online_retail_simulator.simulate": mock_simulate_module}):
            result = adapter.retrieve_business_metrics(products, "2024-01-01", "2024-01-31")

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert "product_id" in result.columns
        assert "sales_volume" in result.columns

    def test_retrieve_business_metrics_not_connected(self):
        """Test retrieving metrics without connection."""
        adapter = CatalogSimulatorAdapter()

        products = pd.DataFrame({"product_id": ["prod1"]})

        with pytest.raises(ConnectionError, match="Not connected to simulator"):
            adapter.retrieve_business_metrics(products, "2024-01-01", "2024-01-31")

    def test_retrieve_business_metrics_empty_products(self):
        """Test retrieving metrics with empty products."""
        adapter = CatalogSimulatorAdapter()
        adapter.connect({"mode": "rule", "seed": 42})

        with pytest.raises(ValueError, match="Products DataFrame cannot be empty"):
            adapter.retrieve_business_metrics(pd.DataFrame(), "2024-01-01", "2024-01-31")

    def test_retrieve_business_metrics_none_products(self):
        """Test retrieving metrics with None products."""
        adapter = CatalogSimulatorAdapter()
        adapter.connect({"mode": "rule", "seed": 42})

        with pytest.raises(ValueError, match="Products DataFrame cannot be empty"):
            adapter.retrieve_business_metrics(None, "2024-01-01", "2024-01-31")

    def test_retrieve_business_metrics_simulator_not_available(self, tmp_path):
        """Test retrieving metrics when simulator package not available."""
        adapter = CatalogSimulatorAdapter()
        adapter.connect({"mode": "rule", "seed": 42, "storage_path": str(tmp_path)})

        products = pd.DataFrame({"product_id": ["prod1"]})

        # Remove the module from sys.modules to simulate it not being available
        with patch.dict("sys.modules", {"online_retail_simulator.simulate": None}):
            with pytest.raises(
                ConnectionError, match="online_retail_simulator package not available"
            ):
                adapter.retrieve_business_metrics(products, "2024-01-01", "2024-01-31")

    def test_retrieve_business_metrics_simulation_error(self, tmp_path):
        """Test retrieving metrics when simulation fails."""
        adapter = CatalogSimulatorAdapter()
        adapter.connect({"mode": "rule", "seed": 42, "storage_path": str(tmp_path)})

        products = pd.DataFrame({"product_id": ["prod1"]})

        # Mock simulate_metrics to raise an exception
        def mock_simulate_metrics_error(job_info, config_path):
            raise Exception("Simulation failed")

        mock_simulate_module = MagicMock()
        mock_simulate_module.simulate_metrics = mock_simulate_metrics_error

        with patch.dict("sys.modules", {"online_retail_simulator.simulate": mock_simulate_module}):
            with pytest.raises(RuntimeError, match="Failed to retrieve metrics"):
                adapter.retrieve_business_metrics(products, "2024-01-01", "2024-01-31")

    def test_transform_inbound_preserves_unknown_columns(self):
        """Test that transform_inbound preserves columns not in MetricsSchema."""
        adapter = CatalogSimulatorAdapter()

        external_data = pd.DataFrame(
            {
                "product_identifier": ["prod1"],
                "date": ["2024-01-01"],
                "ordered_units": [5],
                "revenue": [500.0],
                "enriched": [True],
                "custom_flag": ["abc"],
            }
        )

        result = adapter.transform_inbound(external_data)

        # Schema columns are present
        assert "product_id" in result.columns
        assert "revenue" in result.columns
        # Extra columns survive
        assert "enriched" in result.columns
        assert "custom_flag" in result.columns
        assert result["enriched"].iloc[0] == True  # noqa: E712
        assert result["custom_flag"].iloc[0] == "abc"

    def test_apply_enrichment_returns_enriched_metrics(self, tmp_path):
        """Test that _apply_enrichment returns enriched DF with treatment indicator and quality_score."""
        parent_job = create_job(str(tmp_path), prefix="test-parent")
        adapter = CatalogSimulatorAdapter()
        adapter.connect(
            {
                "mode": "rule",
                "seed": 42,
                "parent_job": parent_job,
                "ENRICHMENT": {
                    "FUNCTION": "product_detail_boost",
                    "PARAMS": {
                        "enrichment_fraction": 0.5,
                        "enrichment_start": "2024-01-08",
                        "quality_boost": 0.15,
                        "seed": 42,
                    },
                },
            }
        )

        metrics_df = pd.DataFrame(
            {
                "product_identifier": ["p1", "p2", "p3", "p4"],
                "date": ["2024-01-08"] * 4,
                "revenue": [100.0, 200.0, 150.0, 120.0],
                "ordered_units": [10, 20, 15, 12],
                "price": [10.0, 10.0, 10.0, 10.0],
            }
        )

        # Mock the enrichment pipeline
        enriched_df = metrics_df.copy()
        enriched_df["enriched"] = [True, False, True, False]
        # Boost revenue for treated products
        enriched_df.loc[enriched_df["enriched"], "revenue"] *= 1.15

        mock_simulate_pd = MagicMock(side_effect=lambda job, cfg: job)

        def mock_enrich(config_path, job):
            job.save_df("enriched", enriched_df)
            # Save product details needed for quality_score
            product_details = pd.DataFrame(
                {
                    "product_identifier": ["p1", "p2", "p3", "p4"],
                    "quality_score": [0.7, 0.6, 0.8, 0.5],
                }
            )
            job.save_df("product_details_original", product_details)
            enriched_details = product_details.copy()
            enriched_details["quality_score"] += 0.15
            job.save_df("product_details_enriched", enriched_details)
            return job

        # Create simulation job (normally done by retrieve_business_metrics)
        adapter._create_simulation_job()

        with patch(
            "online_retail_simulator.simulate.simulate_product_details",
            mock_simulate_pd,
        ), patch(
            "online_retail_simulator.enrich.enrich",
            mock_enrich,
        ):
            result = adapter._apply_enrichment(metrics_df)

        # Should have the enriched column (treatment indicator)
        assert "enriched" in result.columns
        assert result["enriched"].dtype == bool

        # Should have quality_score
        assert "quality_score" in result.columns

        # Treated products should have boosted revenue
        treated = result[result["enriched"]]
        assert all(treated["revenue"] > 100.0)

    def test_available_metrics_initialization(self):
        """Test that available metrics are properly initialized."""
        adapter = CatalogSimulatorAdapter()

        assert hasattr(adapter, "available_metrics")
        assert isinstance(adapter.available_metrics, list)
        assert len(adapter.available_metrics) > 0

        # Check for expected metric types (only actual metrics, not fabricated ones)
        expected_metrics = ["sales_volume", "revenue"]
        for metric in expected_metrics:
            assert metric in adapter.available_metrics
