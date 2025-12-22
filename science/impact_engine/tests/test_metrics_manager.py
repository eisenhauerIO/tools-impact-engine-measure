"""Tests for MetricsManager."""

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from impact_engine.metrics import MetricsInterface, MetricsManager


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


class TestMetricsManagerRegistration:
    """Tests for metrics registration functionality."""

    def test_register_metrics_success(self):
        """Test successful metrics registration."""
        manager = MetricsManager(
            {"TYPE": "simulator", "START_DATE": "2024-01-01", "END_DATE": "2024-01-31"}
        )
        manager.register_metrics("mock", MockMetricsAdapter)

        assert "mock" in manager.get_available_metrics()

    def test_register_metrics_invalid_class(self):
        """Test registering invalid metrics class."""
        manager = MetricsManager(
            {"TYPE": "simulator", "START_DATE": "2024-01-01", "END_DATE": "2024-01-31"}
        )

        class InvalidAdapter:
            pass

        with pytest.raises(ValueError, match="must implement MetricsInterface"):
            manager.register_metrics("invalid", InvalidAdapter)

    def test_get_available_metrics(self):
        """Test getting available metrics types."""
        manager = MetricsManager(
            {"TYPE": "simulator", "START_DATE": "2024-01-01", "END_DATE": "2024-01-31"}
        )

        available = manager.get_available_metrics()
        assert isinstance(available, list)
        assert "simulator" in available  # Built-in adapter


class TestMetricsManagerConfiguration:
    """Tests for configuration handling."""

    def test_load_config_success(self):
        """Test successful configuration loading."""
        config = {
            "TYPE": "simulator",
            "MODE": "rule",
            "SEED": 42,
            "START_DATE": "2024-01-01",
            "END_DATE": "2024-01-31",
        }

        manager = MetricsManager(config)
        assert manager.data_config == config

    def test_load_config_file_success(self):
        """Test loading configuration from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create products CSV
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
                        "START_DATE": "2024-01-01",
                        "END_DATE": "2024-01-31",
                        "INTERVENTION_DATE": "2024-01-15",
                    },
                },
            }
            config_path = str(Path(tmpdir) / "config.json")
            with open(config_path, "w") as f:
                json.dump(config, f)

            manager = MetricsManager.from_config_file(config_path)
            assert manager.data_config == config["DATA"]

    def test_load_config_file_not_found(self):
        """Test loading from non-existent config file."""
        with pytest.raises(FileNotFoundError):
            MetricsManager.from_config_file("non_existent_file.json")

    def test_validate_config_missing_type(self):
        """Test validation with missing TYPE field."""
        with pytest.raises(ValueError, match="Missing required field 'TYPE'"):
            MetricsManager({"START_DATE": "2024-01-01", "END_DATE": "2024-01-31"})

    def test_validate_config_missing_start_date(self):
        """Test validation with missing START_DATE field."""
        with pytest.raises(ValueError, match="Missing required field 'START_DATE'"):
            MetricsManager({"TYPE": "simulator", "END_DATE": "2024-01-31"})

    def test_validate_config_missing_end_date(self):
        """Test validation with missing END_DATE field."""
        with pytest.raises(ValueError, match="Missing required field 'END_DATE'"):
            MetricsManager({"TYPE": "simulator", "START_DATE": "2024-01-01"})

    def test_validate_config_invalid_date_format(self):
        """Test validation with invalid date format."""
        with pytest.raises(ValueError, match="Invalid date format"):
            MetricsManager(
                {"TYPE": "simulator", "START_DATE": "invalid-date", "END_DATE": "2024-01-31"}
            )

    def test_validate_config_invalid_date_order(self):
        """Test validation with start date after end date."""
        with pytest.raises(ValueError, match="START_DATE must be before or equal to END_DATE"):
            MetricsManager(
                {"TYPE": "simulator", "START_DATE": "2024-01-31", "END_DATE": "2024-01-01"}
            )

    def test_get_current_config(self):
        """Test getting current configuration."""
        config = {"TYPE": "simulator", "START_DATE": "2024-01-01", "END_DATE": "2024-01-31"}

        manager = MetricsManager(config)
        assert manager.get_current_config() == config


class TestMetricsManagerGetSource:
    """Tests for getting metrics sources."""

    def test_get_metrics_source_by_type(self):
        """Test getting metrics source by explicit type."""
        manager = MetricsManager(
            {"TYPE": "simulator", "START_DATE": "2024-01-01", "END_DATE": "2024-01-31"}
        )
        manager.register_metrics("mock", MockMetricsAdapter)

        source = manager.get_metrics_source("mock")
        assert isinstance(source, MockMetricsAdapter)
        assert source.is_connected is True

    def test_get_metrics_source_from_config(self):
        """Test getting metrics source from configuration."""
        manager = MetricsManager(
            {
                "TYPE": "simulator",
                "MODE": "rule",
                "SEED": 42,
                "START_DATE": "2024-01-01",
                "END_DATE": "2024-01-31",
            }
        )

        source = manager.get_metrics_source()
        assert source is not None

    def test_get_metrics_source_unknown_type(self):
        """Test getting unknown metrics source type."""
        manager = MetricsManager(
            {"TYPE": "simulator", "START_DATE": "2024-01-01", "END_DATE": "2024-01-31"}
        )

        with pytest.raises(ValueError, match="Unknown metrics type 'unknown'"):
            manager.get_metrics_source("unknown")


class TestMetricsManagerRetrieveMetrics:
    """Tests for metrics retrieval."""

    def test_retrieve_metrics_success(self):
        """Test successful metrics retrieval."""
        manager = MetricsManager(
            {
                "TYPE": "simulator",
                "MODE": "rule",
                "SEED": 42,
                "START_DATE": "2024-01-01",
                "END_DATE": "2024-01-31",
            }
        )
        manager.register_metrics("mock", MockMetricsAdapter)

        # Override the config to use mock
        manager.data_config["TYPE"] = "mock"

        products = pd.DataFrame({"product_id": ["test_product"], "name": ["Test Product"]})

        result = manager.retrieve_metrics(products)

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert "product_id" in result.columns

    def test_retrieve_metrics_empty_products(self):
        """Test retrieving metrics with empty products."""
        manager = MetricsManager(
            {"TYPE": "simulator", "START_DATE": "2024-01-01", "END_DATE": "2024-01-31"}
        )

        with pytest.raises(ValueError, match="Products DataFrame cannot be empty"):
            manager.retrieve_metrics(pd.DataFrame())

    def test_retrieve_metrics_none_products(self):
        """Test retrieving metrics with None products."""
        manager = MetricsManager(
            {"TYPE": "simulator", "START_DATE": "2024-01-01", "END_DATE": "2024-01-31"}
        )

        with pytest.raises(ValueError, match="Products DataFrame cannot be empty"):
            manager.retrieve_metrics(None)
