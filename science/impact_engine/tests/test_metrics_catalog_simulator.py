"""Tests for CatalogSimulatorAdapter."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from artifact_store import create_job

from impact_engine.metrics import CatalogSimulatorAdapter


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

    def test_connect_invalid_mode(self):
        """Test connection with invalid mode."""
        adapter = CatalogSimulatorAdapter()

        with pytest.raises(ValueError, match="Invalid simulator mode 'invalid'"):
            adapter.connect({"mode": "invalid"})

    def test_connect_invalid_seed(self):
        """Test connection with invalid seed."""
        adapter = CatalogSimulatorAdapter()

        with pytest.raises(ValueError, match="Simulator seed must be a non-negative integer"):
            adapter.connect({"seed": -1})

    def test_connect_default_values(self):
        """Test connection with default values."""
        adapter = CatalogSimulatorAdapter()

        result = adapter.connect({})
        assert result is True
        assert adapter.config["mode"] == "rule"
        assert adapter.config["seed"] == 42

    def test_validate_connection_success(self):
        """Test connection validation when connected and simulator available."""
        adapter = CatalogSimulatorAdapter()
        adapter.connect({"mode": "rule"})

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
        adapter.connect({"mode": "rule"})

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

        # Check product characteristics (should have asin mapped from product_id)
        prod_chars = result["product_characteristics"]
        assert "asin" in prod_chars.columns
        assert "name" in prod_chars.columns
        assert "category" in prod_chars.columns
        assert "price" in prod_chars.columns

        # Check rule config structure
        rule_config = result["rule_config"]
        assert "CHARACTERISTICS" in rule_config
        assert "METRICS" in rule_config
        assert rule_config["METRICS"]["PARAMS"]["date_start"] == "2024-01-01"
        assert rule_config["METRICS"]["PARAMS"]["date_end"] == "2024-01-31"
        assert rule_config["METRICS"]["PARAMS"]["seed"] == 42

    def test_transform_outbound_missing_product_id(self):
        """Test outbound transformation with missing product_id column."""
        adapter = CatalogSimulatorAdapter()
        adapter.connect({"mode": "rule"})

        products = pd.DataFrame({"name": ["Product 1"], "category": ["Electronics"]})

        result = adapter.transform_outbound(products, "2024-01-01", "2024-01-31")

        # Should create asin from index
        prod_chars = result["product_characteristics"]
        assert "asin" in prod_chars.columns
        assert prod_chars["asin"].iloc[0] == "0"

    def test_transform_outbound_missing_optional_columns(self):
        """Test outbound transformation with missing optional columns."""
        adapter = CatalogSimulatorAdapter()
        adapter.connect({"mode": "rule"})

        products = pd.DataFrame({"product_id": ["prod1"]})

        result = adapter.transform_outbound(products, "2024-01-01", "2024-01-31")

        prod_chars = result["product_characteristics"]
        assert "asin" in prod_chars.columns
        assert prod_chars["asin"].iloc[0] == "prod1"
        # Optional columns (name, category, price) are not fabricated

    def test_transform_inbound_success(self):
        """Test successful inbound transformation."""
        adapter = CatalogSimulatorAdapter()

        # Mock RuleBackend output (uses asin and ordered_units)
        external_data = pd.DataFrame(
            {
                "asin": ["prod1"],
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
        assert "product_id" in result.columns  # asin mapped to product_id
        assert "sales_volume" in result.columns  # ordered_units mapped to sales_volume
        assert "revenue" in result.columns
        assert "metrics_source" in result.columns
        assert "retrieval_timestamp" in result.columns
        # inventory_level and customer_engagement are not fabricated

        # Check that asin was mapped to product_id
        assert result["product_id"].iloc[0] == "prod1"
        # Check that ordered_units was mapped to sales_volume
        assert result["sales_volume"].iloc[0] == 5
        assert result["metrics_source"].iloc[0] == "catalog_simulator"

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
                    "asin": ["prod1"],
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
        adapter.connect({"mode": "rule"})

        with pytest.raises(ValueError, match="Products DataFrame cannot be empty"):
            adapter.retrieve_business_metrics(pd.DataFrame(), "2024-01-01", "2024-01-31")

    def test_retrieve_business_metrics_none_products(self):
        """Test retrieving metrics with None products."""
        adapter = CatalogSimulatorAdapter()
        adapter.connect({"mode": "rule"})

        with pytest.raises(ValueError, match="Products DataFrame cannot be empty"):
            adapter.retrieve_business_metrics(None, "2024-01-01", "2024-01-31")

    def test_retrieve_business_metrics_simulator_not_available(self, tmp_path):
        """Test retrieving metrics when simulator package not available."""
        adapter = CatalogSimulatorAdapter()
        adapter.connect({"mode": "rule", "storage_path": str(tmp_path)})

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
        adapter.connect({"mode": "rule", "storage_path": str(tmp_path)})

        products = pd.DataFrame({"product_id": ["prod1"]})

        # Mock simulate_metrics to raise an exception
        def mock_simulate_metrics_error(job_info, config_path):
            raise Exception("Simulation failed")

        mock_simulate_module = MagicMock()
        mock_simulate_module.simulate_metrics = mock_simulate_metrics_error

        with patch.dict("sys.modules", {"online_retail_simulator.simulate": mock_simulate_module}):
            with pytest.raises(RuntimeError, match="Failed to retrieve metrics"):
                adapter.retrieve_business_metrics(products, "2024-01-01", "2024-01-31")

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
