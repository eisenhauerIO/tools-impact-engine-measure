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
from impact_engine.metrics.factory import METRICS_REGISTRY


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


def complete_source_config(**overrides):
    """Create a complete SOURCE.CONFIG with defaults.

    Tests that bypass process_config() must provide complete configs.
    """
    config = {
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "mode": "rule",
        "seed": 42,
    }
    config.update(overrides)
    return config


class TestMetricsManagerDependencyInjection:
    """Tests for dependency injection pattern."""

    def test_create_with_injected_adapter(self):
        """Test creating manager with injected adapter."""
        mock_adapter = MockMetricsAdapter()
        config = complete_source_config()

        manager = MetricsManager(config, mock_adapter)

        assert manager.metrics_source is mock_adapter
        assert mock_adapter.is_connected is True

    def test_create_with_mock_spec(self):
        """Test creating manager with Mock(spec=MetricsInterface)."""
        mock_adapter = Mock(spec=MetricsInterface)
        mock_adapter.connect.return_value = True

        config = complete_source_config()

        manager = MetricsManager(config, mock_adapter)

        mock_adapter.connect.assert_called_once()
        assert manager.metrics_source is mock_adapter

    def test_adapter_receives_connection_config(self):
        """Test that adapter receives proper connection config."""
        mock_adapter = MockMetricsAdapter()
        config = complete_source_config(mode="ml", seed=123)

        MetricsManager(config, mock_adapter)

        assert mock_adapter.config["mode"] == "ml"
        assert mock_adapter.config["seed"] == 123

    def test_adapter_receives_enrichment_config(self):
        """Test that enrichment config is passed to adapter."""
        mock_adapter = MockMetricsAdapter()
        enrichment = {"FUNCTION": "quantity_boost", "PARAMS": {"effect_size": 0.3}}
        config = complete_source_config(ENRICHMENT=enrichment)

        MetricsManager(config, mock_adapter)

        assert mock_adapter.config["enrichment"] == enrichment


class TestMetricsManagerConfiguration:
    """Tests for configuration handling.

    Note: Validation is now centralized in process_config().
    These tests verify the manager works with complete configs.
    """

    def test_get_current_config(self):
        """Test getting current configuration."""
        mock_adapter = MockMetricsAdapter()
        config = complete_source_config()

        manager = MetricsManager(config, mock_adapter)
        assert manager.get_current_config() == config


class TestMetricsManagerRetrieveMetrics:
    """Tests for metrics retrieval."""

    def test_retrieve_metrics_success(self):
        """Test successful metrics retrieval."""
        mock_adapter = MockMetricsAdapter()
        config = complete_source_config()

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

        config = complete_source_config()
        manager = MetricsManager(config, mock_adapter)

        products = pd.DataFrame({"product_id": ["p1"]})
        manager.retrieve_metrics(products)

        mock_adapter.retrieve_business_metrics.assert_called_once_with(
            products=products, start_date="2024-01-01", end_date="2024-01-31"
        )

    def test_retrieve_metrics_empty_products(self):
        """Test retrieving metrics with empty products."""
        mock_adapter = MockMetricsAdapter()
        config = complete_source_config()

        manager = MetricsManager(config, mock_adapter)

        with pytest.raises(ValueError, match="Products DataFrame cannot be empty"):
            manager.retrieve_metrics(pd.DataFrame())

    def test_retrieve_metrics_none_products(self):
        """Test retrieving metrics with None products."""
        mock_adapter = MockMetricsAdapter()
        config = complete_source_config()

        manager = MetricsManager(config, mock_adapter)

        with pytest.raises(ValueError, match="Products DataFrame cannot be empty"):
            manager.retrieve_metrics(None)


class TestMetricsFactory:
    """Tests for factory functions."""

    def test_create_metrics_manager_from_config_dict(self):
        """Test creating manager from config dict."""
        # Register mock adapter
        METRICS_REGISTRY.register("mock", MockMetricsAdapter)

        try:
            config = complete_source_config(TYPE="mock")

            manager = create_metrics_manager_from_config(config)

            assert isinstance(manager, MetricsManager)
            assert isinstance(manager.metrics_source, MockMetricsAdapter)
        finally:
            # Clean up
            del METRICS_REGISTRY._registry["mock"]

    def test_create_metrics_manager_from_file(self):
        """Test creating manager from config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            products_path = str(Path(tmpdir) / "products.csv")
            pd.DataFrame({"product_id": ["p1"]}).to_csv(products_path, index=False)

            # Use new SOURCE/TRANSFORM config structure
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
                        "intervention_date": "2024-01-15",
                    },
                },
            }
            config_path = str(Path(tmpdir) / "config.json")
            with open(config_path, "w") as f:
                json.dump(config, f)

            manager = create_metrics_manager(config_path)

            assert isinstance(manager, MetricsManager)
            # source_config is now the SOURCE.CONFIG part
            assert manager.source_config == config["DATA"]["SOURCE"]["CONFIG"]

    def test_create_metrics_manager_unknown_type(self):
        """Test creating manager with unknown adapter type."""
        config = complete_source_config(TYPE="unknown_type")

        with pytest.raises(ValueError, match="Unknown metrics adapter"):
            create_metrics_manager_from_config(config)

    def test_register_invalid_adapter(self):
        """Test registering invalid adapter class."""

        class InvalidAdapter:
            pass

        with pytest.raises(ValueError, match="must implement MetricsInterface"):
            METRICS_REGISTRY.register("invalid", InvalidAdapter)


class TestMetricsManagerConnectionFailure:
    """Tests for connection failure handling."""

    def test_connection_failure_raises_error(self):
        """Test that connection failure raises ConnectionError."""
        mock_adapter = Mock(spec=MetricsInterface)
        mock_adapter.connect.return_value = False

        config = complete_source_config()

        with pytest.raises(ConnectionError, match="Failed to connect"):
            MetricsManager(config, mock_adapter)
