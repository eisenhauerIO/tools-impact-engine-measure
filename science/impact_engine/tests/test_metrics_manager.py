"""Tests for MetricsManager with dependency injection."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

from impact_engine.metrics import (
    MetricsInterface,
    MetricsManager,
    create_metrics_manager,
    create_metrics_manager_from_config,
)
from impact_engine.metrics.factory import METRICS_ADAPTERS, register_metrics_adapter


class MockMetricsAdapter(MetricsInterface):
    """Mock metrics adapter for testing."""

    def __init__(self):
        self.is_connected = False
        self.config = None

    def connect(self, config):
        """Mock connect method."""
        self.config = config
        self.is_connected = True
        return True

    def validate_connection(self):
        """Mock validate_connection method."""
        return self.is_connected

    def transform_outbound(self, products, start_date, end_date):
        """Mock transform_outbound method."""
        return {"products": products, "start_date": start_date, "end_date": end_date}

    def transform_inbound(self, external_data):
        """Mock transform_inbound method."""
        return pd.DataFrame(
            {"product_id": ["test_product"], "revenue": [1000], "date": ["2024-01-01"]}
        )

    def retrieve_business_metrics(self, products, start_date, end_date):
        """Mock retrieve_business_metrics method."""
        if not self.is_connected:
            raise ConnectionError("Not connected")

        return pd.DataFrame(
            {
                "product_id": ["test_product"] * len(products),
                "revenue": [1000] * len(products),
                "date": [start_date] * len(products),
            }
        )


class TestMetricsManagerDependencyInjection:
    """Tests for dependency injection pattern."""

    def test_create_with_injected_adapter(self):
        """Test creating manager with injected adapter."""
        mock_adapter = MockMetricsAdapter()
        config = {"START_DATE": "2024-01-01", "END_DATE": "2024-01-31"}

        manager = MetricsManager(config, mock_adapter)

        assert manager.metrics_source is mock_adapter
        assert mock_adapter.is_connected is True

    def test_create_with_mock_spec(self):
        """Test creating manager with Mock(spec=MetricsInterface)."""
        mock_adapter = Mock(spec=MetricsInterface)
        mock_adapter.connect.return_value = True

        config = {"START_DATE": "2024-01-01", "END_DATE": "2024-01-31"}

        manager = MetricsManager(config, mock_adapter)

        mock_adapter.connect.assert_called_once()
        assert manager.metrics_source is mock_adapter

    def test_adapter_receives_connection_config(self):
        """Test that adapter receives proper connection config."""
        mock_adapter = MockMetricsAdapter()
        config = {
            "START_DATE": "2024-01-01",
            "END_DATE": "2024-01-31",
            "MODE": "ml",
            "SEED": 123,
        }

        MetricsManager(config, mock_adapter)

        assert mock_adapter.config["mode"] == "ml"
        assert mock_adapter.config["seed"] == 123

    def test_adapter_receives_enrichment_config(self):
        """Test that enrichment config is passed to adapter."""
        mock_adapter = MockMetricsAdapter()
        enrichment = {"function": "quantity_boost", "params": {"effect_size": 0.3}}
        config = {
            "START_DATE": "2024-01-01",
            "END_DATE": "2024-01-31",
            "ENRICHMENT": enrichment,
        }

        MetricsManager(config, mock_adapter)

        assert mock_adapter.config["enrichment"] == enrichment


class TestMetricsManagerConfiguration:
    """Tests for configuration handling."""

    def test_validate_config_missing_start_date(self):
        """Test validation with missing START_DATE field."""
        mock_adapter = MockMetricsAdapter()
        with pytest.raises(ValueError, match="Missing required field 'START_DATE'"):
            MetricsManager({"END_DATE": "2024-01-31"}, mock_adapter)

    def test_validate_config_missing_end_date(self):
        """Test validation with missing END_DATE field."""
        mock_adapter = MockMetricsAdapter()
        with pytest.raises(ValueError, match="Missing required field 'END_DATE'"):
            MetricsManager({"START_DATE": "2024-01-01"}, mock_adapter)

    def test_validate_config_invalid_date_format(self):
        """Test validation with invalid date format."""
        mock_adapter = MockMetricsAdapter()
        with pytest.raises(ValueError, match="Invalid date format"):
            MetricsManager({"START_DATE": "invalid-date", "END_DATE": "2024-01-31"}, mock_adapter)

    def test_validate_config_invalid_date_order(self):
        """Test validation with start date after end date."""
        mock_adapter = MockMetricsAdapter()
        with pytest.raises(ValueError, match="START_DATE must be before or equal to END_DATE"):
            MetricsManager({"START_DATE": "2024-01-31", "END_DATE": "2024-01-01"}, mock_adapter)

    def test_get_current_config(self):
        """Test getting current configuration."""
        mock_adapter = MockMetricsAdapter()
        config = {"START_DATE": "2024-01-01", "END_DATE": "2024-01-31"}

        manager = MetricsManager(config, mock_adapter)
        assert manager.get_current_config() == config


class TestMetricsManagerRetrieveMetrics:
    """Tests for metrics retrieval."""

    def test_retrieve_metrics_success(self):
        """Test successful metrics retrieval."""
        mock_adapter = MockMetricsAdapter()
        config = {"START_DATE": "2024-01-01", "END_DATE": "2024-01-31"}

        manager = MetricsManager(config, mock_adapter)
        products = pd.DataFrame({"product_id": ["test_product"], "name": ["Test Product"]})

        result = manager.retrieve_metrics(products)

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert "product_id" in result.columns

    def test_retrieve_metrics_calls_adapter(self):
        """Test that retrieve_metrics calls the adapter correctly."""
        mock_adapter = Mock(spec=MetricsInterface)
        mock_adapter.connect.return_value = True
        mock_adapter.retrieve_business_metrics.return_value = pd.DataFrame(
            {"product_id": ["p1"], "revenue": [100], "date": ["2024-01-01"]}
        )

        config = {"START_DATE": "2024-01-01", "END_DATE": "2024-01-31"}
        manager = MetricsManager(config, mock_adapter)

        products = pd.DataFrame({"product_id": ["p1"]})
        manager.retrieve_metrics(products)

        mock_adapter.retrieve_business_metrics.assert_called_once_with(
            products=products, start_date="2024-01-01", end_date="2024-01-31"
        )

    def test_retrieve_metrics_empty_products(self):
        """Test retrieving metrics with empty products."""
        mock_adapter = MockMetricsAdapter()
        config = {"START_DATE": "2024-01-01", "END_DATE": "2024-01-31"}

        manager = MetricsManager(config, mock_adapter)

        with pytest.raises(ValueError, match="Products DataFrame cannot be empty"):
            manager.retrieve_metrics(pd.DataFrame())

    def test_retrieve_metrics_none_products(self):
        """Test retrieving metrics with None products."""
        mock_adapter = MockMetricsAdapter()
        config = {"START_DATE": "2024-01-01", "END_DATE": "2024-01-31"}

        manager = MetricsManager(config, mock_adapter)

        with pytest.raises(ValueError, match="Products DataFrame cannot be empty"):
            manager.retrieve_metrics(None)


class TestMetricsFactory:
    """Tests for factory functions."""

    def test_create_metrics_manager_from_config_dict(self):
        """Test creating manager from config dict."""
        # Register mock adapter
        register_metrics_adapter("mock", MockMetricsAdapter)

        try:
            config = {
                "TYPE": "mock",
                "START_DATE": "2024-01-01",
                "END_DATE": "2024-01-31",
            }

            manager = create_metrics_manager_from_config(config)

            assert isinstance(manager, MetricsManager)
            assert isinstance(manager.metrics_source, MockMetricsAdapter)
        finally:
            # Clean up
            del METRICS_ADAPTERS["mock"]

    def test_create_metrics_manager_from_file(self):
        """Test creating manager from config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            products_path = str(Path(tmpdir) / "products.csv")
            pd.DataFrame({"product_id": ["p1"]}).to_csv(products_path, index=False)

            config = {
                "DATA": {
                    "TYPE": "simulator",
                    "PATH": products_path,
                    "MODE": "rule",
                    "SEED": 42,
                    "START_DATE": "2024-01-01",
                    "END_DATE": "2024-01-31",
                },
                "MEASUREMENT": {
                    "MODEL": "interrupted_time_series",
                    "PARAMS": {
                        "INTERVENTION_DATE": "2024-01-15",
                    },
                },
            }
            config_path = str(Path(tmpdir) / "config.json")
            with open(config_path, "w") as f:
                json.dump(config, f)

            manager = create_metrics_manager(config_path)

            assert isinstance(manager, MetricsManager)
            assert manager.data_config == config["DATA"]

    def test_create_metrics_manager_unknown_type(self):
        """Test creating manager with unknown adapter type."""
        config = {
            "TYPE": "unknown_type",
            "START_DATE": "2024-01-01",
            "END_DATE": "2024-01-31",
        }

        with pytest.raises(ValueError, match="Unknown metrics type"):
            create_metrics_manager_from_config(config)

    def test_register_invalid_adapter(self):
        """Test registering invalid adapter class."""

        class InvalidAdapter:
            pass

        with pytest.raises(ValueError, match="must implement MetricsInterface"):
            register_metrics_adapter("invalid", InvalidAdapter)


class TestMetricsManagerConnectionFailure:
    """Tests for connection failure handling."""

    def test_connection_failure_raises_error(self):
        """Test that connection failure raises ConnectionError."""
        mock_adapter = Mock(spec=MetricsInterface)
        mock_adapter.connect.return_value = False

        config = {"START_DATE": "2024-01-01", "END_DATE": "2024-01-31"}

        with pytest.raises(ConnectionError, match="Failed to connect"):
            MetricsManager(config, mock_adapter)
