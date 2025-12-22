"""Tests for configuration bridge module."""

from impact_engine.core import ConfigBridge


class TestConfigBridgeToCatalogSimulator:
    """Tests for ConfigBridge.to_catalog_simulator()."""

    def test_basic_conversion(self):
        """Converts basic impact-engine config to catalog-simulator format."""
        ie_config = {
            "DATA": {
                "TYPE": "simulator",
                "MODE": "rule",
                "SEED": 42,
                "START_DATE": "2024-01-01",
                "END_DATE": "2024-01-31",
            }
        }
        result = ConfigBridge.to_catalog_simulator(ie_config, num_products=50)

        assert "RULE" in result
        assert "CHARACTERISTICS" in result["RULE"]
        assert "METRICS" in result["RULE"]

    def test_dates_mapped_correctly(self):
        """START_DATE and END_DATE mapped to date_start and date_end."""
        ie_config = {
            "DATA": {
                "START_DATE": "2024-03-01",
                "END_DATE": "2024-03-31",
            }
        }
        result = ConfigBridge.to_catalog_simulator(ie_config)
        metrics_params = result["RULE"]["METRICS"]["PARAMS"]

        assert metrics_params["date_start"] == "2024-03-01"
        assert metrics_params["date_end"] == "2024-03-31"

    def test_seed_propagated(self):
        """SEED propagated to both CHARACTERISTICS and METRICS."""
        ie_config = {
            "DATA": {
                "SEED": 123,
                "START_DATE": "2024-01-01",
                "END_DATE": "2024-01-31",
            }
        }
        result = ConfigBridge.to_catalog_simulator(ie_config)

        assert result["RULE"]["CHARACTERISTICS"]["PARAMS"]["seed"] == 123
        assert result["RULE"]["METRICS"]["PARAMS"]["seed"] == 123

    def test_num_products_parameter(self):
        """num_products parameter sets CHARACTERISTICS.PARAMS.num_products."""
        ie_config = {"DATA": {"START_DATE": "2024-01-01", "END_DATE": "2024-01-31"}}
        result = ConfigBridge.to_catalog_simulator(ie_config, num_products=200)

        assert result["RULE"]["CHARACTERISTICS"]["PARAMS"]["num_products"] == 200

    def test_enrichment_mapping(self):
        """ENRICHMENT section mapped to IMPACT block."""
        ie_config = {
            "DATA": {
                "START_DATE": "2024-01-01",
                "END_DATE": "2024-01-31",
                "ENRICHMENT": {
                    "function": "quantity_boost",
                    "params": {
                        "effect_size": 0.3,
                        "enrichment_start": "2024-01-15",
                    },
                },
            }
        }
        result = ConfigBridge.to_catalog_simulator(ie_config)

        assert "IMPACT" in result
        assert result["IMPACT"]["FUNCTION"] == "quantity_boost"
        assert result["IMPACT"]["PARAMS"]["effect_size"] == 0.3
        assert result["IMPACT"]["PARAMS"]["enrichment_start"] == "2024-01-15"

    def test_no_enrichment(self):
        """No IMPACT block when ENRICHMENT not present."""
        ie_config = {
            "DATA": {
                "START_DATE": "2024-01-01",
                "END_DATE": "2024-01-31",
            }
        }
        result = ConfigBridge.to_catalog_simulator(ie_config)

        assert "IMPACT" not in result

    def test_default_seed(self):
        """Default seed is 42 when not specified."""
        ie_config = {
            "DATA": {
                "START_DATE": "2024-01-01",
                "END_DATE": "2024-01-31",
            }
        }
        result = ConfigBridge.to_catalog_simulator(ie_config)

        assert result["RULE"]["METRICS"]["PARAMS"]["seed"] == 42

    def test_funnel_params_included(self):
        """Funnel parameters (sale_prob, rates) included in METRICS."""
        ie_config = {"DATA": {"START_DATE": "2024-01-01", "END_DATE": "2024-01-31"}}
        result = ConfigBridge.to_catalog_simulator(ie_config)
        params = result["RULE"]["METRICS"]["PARAMS"]

        assert "sale_prob" in params
        assert "impression_to_visit_rate" in params
        assert "visit_to_cart_rate" in params
        assert "cart_to_order_rate" in params


class TestConfigBridgeFromCatalogSimulator:
    """Tests for ConfigBridge.from_catalog_simulator()."""

    def test_basic_conversion(self):
        """Converts basic catalog-simulator config to impact-engine format."""
        cs_config = {
            "RULE": {
                "METRICS": {
                    "PARAMS": {
                        "date_start": "2024-01-01",
                        "date_end": "2024-01-31",
                        "seed": 42,
                    }
                }
            }
        }
        result = ConfigBridge.from_catalog_simulator(cs_config)

        assert "DATA" in result
        assert result["DATA"]["TYPE"] == "simulator"
        assert result["DATA"]["MODE"] == "rule"

    def test_dates_mapped_correctly(self):
        """date_start and date_end mapped to START_DATE and END_DATE."""
        cs_config = {
            "RULE": {
                "METRICS": {
                    "PARAMS": {
                        "date_start": "2024-03-01",
                        "date_end": "2024-03-31",
                    }
                }
            }
        }
        result = ConfigBridge.from_catalog_simulator(cs_config)

        assert result["DATA"]["START_DATE"] == "2024-03-01"
        assert result["DATA"]["END_DATE"] == "2024-03-31"

    def test_seed_mapped(self):
        """Seed value mapped correctly."""
        cs_config = {"RULE": {"METRICS": {"PARAMS": {"seed": 999}}}}
        result = ConfigBridge.from_catalog_simulator(cs_config)

        assert result["DATA"]["SEED"] == 999

    def test_synthesizer_mode(self):
        """SYNTHESIZER key results in MODE=ml."""
        cs_config = {
            "SYNTHESIZER": {
                "METRICS": {
                    "PARAMS": {
                        "date_start": "2024-01-01",
                        "date_end": "2024-01-31",
                    }
                }
            }
        }
        result = ConfigBridge.from_catalog_simulator(cs_config)

        assert result["DATA"]["MODE"] == "ml"

    def test_impact_to_enrichment(self):
        """IMPACT block mapped to ENRICHMENT."""
        cs_config = {
            "RULE": {"METRICS": {"PARAMS": {}}},
            "IMPACT": {
                "FUNCTION": "quantity_boost",
                "PARAMS": {"effect_size": 0.5},
            },
        }
        result = ConfigBridge.from_catalog_simulator(cs_config)

        assert "ENRICHMENT" in result["DATA"]
        assert result["DATA"]["ENRICHMENT"]["function"] == "quantity_boost"
        assert result["DATA"]["ENRICHMENT"]["params"]["effect_size"] == 0.5


class TestConfigBridgeBuildEnrichmentConfig:
    """Tests for ConfigBridge.build_enrichment_config()."""

    def test_basic_enrichment(self):
        """Builds IMPACT config from enrichment dict."""
        enrichment = {
            "function": "quantity_boost",
            "params": {"effect_size": 0.3},
        }
        result = ConfigBridge.build_enrichment_config(enrichment)

        assert "IMPACT" in result
        assert result["IMPACT"]["FUNCTION"] == "quantity_boost"
        assert result["IMPACT"]["PARAMS"]["effect_size"] == 0.3

    def test_empty_params(self):
        """Handles missing params gracefully."""
        enrichment = {"function": "some_function"}
        result = ConfigBridge.build_enrichment_config(enrichment)

        assert result["IMPACT"]["FUNCTION"] == "some_function"
        assert result["IMPACT"]["PARAMS"] == {}


class TestConfigBridgeRoundtrip:
    """Tests for roundtrip conversion."""

    def test_roundtrip_preserves_core_fields(self):
        """Converting to catalog_simulator and back preserves core fields."""
        original = {
            "DATA": {
                "TYPE": "simulator",
                "MODE": "rule",
                "SEED": 42,
                "START_DATE": "2024-01-01",
                "END_DATE": "2024-01-31",
            }
        }
        cs_config = ConfigBridge.to_catalog_simulator(original)
        back = ConfigBridge.from_catalog_simulator(cs_config)

        assert back["DATA"]["START_DATE"] == original["DATA"]["START_DATE"]
        assert back["DATA"]["END_DATE"] == original["DATA"]["END_DATE"]
        assert back["DATA"]["SEED"] == original["DATA"]["SEED"]

    def test_roundtrip_with_enrichment(self):
        """Roundtrip preserves enrichment configuration."""
        original = {
            "DATA": {
                "START_DATE": "2024-01-01",
                "END_DATE": "2024-01-31",
                "ENRICHMENT": {
                    "function": "quantity_boost",
                    "params": {"effect_size": 0.3},
                },
            }
        }
        cs_config = ConfigBridge.to_catalog_simulator(original)
        back = ConfigBridge.from_catalog_simulator(cs_config)

        assert back["DATA"]["ENRICHMENT"]["function"] == "quantity_boost"
        assert back["DATA"]["ENRICHMENT"]["params"]["effect_size"] == 0.3
