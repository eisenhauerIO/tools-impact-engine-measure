"""
Configuration bridge for translating between impact-engine and external systems.

This module provides bidirectional translation between configuration schemas,
ensuring libraries communicate only through well-defined config formats.
"""

from typing import Any, Dict

from .validation import get_defaults


def _get_catalog_simulator_defaults() -> Dict[str, Any]:
    """Get catalog simulator defaults from config_defaults.yaml."""
    defaults = get_defaults()
    return defaults["CATALOG_SIMULATOR"]


class ConfigBridge:
    """Translates configuration between impact-engine and external systems."""

    @staticmethod
    def to_catalog_simulator(
        ie_config: Dict[str, Any],
        num_products: int = 100,
    ) -> Dict[str, Any]:
        """
        Convert impact-engine config to catalog-simulator format.

        Args:
            ie_config: Impact-engine configuration dict with DATA section
            num_products: Number of products (from actual products DataFrame)

        Returns:
            Catalog-simulator compatible configuration

        Example input (flat dict built by adapter, not full user config):
            DATA:
              start_date: "2024-01-01"
              end_date: "2024-01-31"
              seed: 42

        Example output (catalog-simulator format):
            RULE:
              PRODUCTS:
                FUNCTION: simulate_products_rule_based
                PARAMS: {num_products: 100, seed: 42}
              METRICS:
                FUNCTION: simulate_metrics_rule_based
                PARAMS:
                  date_start: "2024-01-01"
                  date_end: "2024-01-31"
                  seed: 42
            IMPACT:
              FUNCTION: quantity_boost
              PARAMS:
                effect_size: 0.3
                enrichment_start: "2024-01-15"
        """
        data = ie_config.get("DATA", {})
        seed = data.get("seed", 42)

        # Get simulation defaults from config
        sim_defaults = _get_catalog_simulator_defaults()

        # Build RULE config
        cs_config: Dict[str, Any] = {
            "RULE": {
                "PRODUCTS": {
                    "FUNCTION": "simulate_products_rule_based",
                    "PARAMS": {"num_products": num_products, "seed": seed},
                },
                "METRICS": {
                    "FUNCTION": "simulate_metrics_rule_based",
                    "PARAMS": {
                        "date_start": data.get("start_date"),
                        "date_end": data.get("end_date"),
                        "seed": seed,
                        "sale_prob": sim_defaults["sale_prob"],
                        "granularity": "daily",
                        "impression_to_visit_rate": sim_defaults["impression_to_visit_rate"],
                        "visit_to_cart_rate": sim_defaults["visit_to_cart_rate"],
                        "cart_to_order_rate": sim_defaults["cart_to_order_rate"],
                    },
                },
            }
        }

        # Map enrichment if present
        if "ENRICHMENT" in data:
            enrichment = data["ENRICHMENT"]
            cs_config["IMPACT"] = {
                "FUNCTION": enrichment.get("FUNCTION"),
                "PARAMS": enrichment.get("PARAMS", {}),
            }

        return cs_config

    @staticmethod
    def from_catalog_simulator(cs_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert catalog-simulator config to impact-engine format.

        Args:
            cs_config: Catalog-simulator configuration dict

        Returns:
            Impact-engine compatible configuration
        """
        rule = cs_config.get("RULE", cs_config.get("SYNTHESIZER", {}))
        metrics_params = rule.get("METRICS", {}).get("PARAMS", {})

        ie_config: Dict[str, Any] = {
            "DATA": {
                "type": "simulator",
                "mode": "rule" if "RULE" in cs_config else "ml",
                "start_date": metrics_params.get("date_start"),
                "end_date": metrics_params.get("date_end"),
                "seed": metrics_params.get("seed", 42),
            }
        }

        # Map enrichment back
        if "IMPACT" in cs_config:
            impact = cs_config["IMPACT"]
            ie_config["DATA"]["ENRICHMENT"] = {
                "FUNCTION": impact.get("FUNCTION"),
                "PARAMS": impact.get("PARAMS", {}),
            }

        return ie_config

    @staticmethod
    def build_enrichment_config(enrichment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build catalog-simulator IMPACT config from enrichment settings.

        Args:
            enrichment: Enrichment config with 'function' and 'params'

        Returns:
            Catalog-simulator IMPACT configuration block
        """
        return {
            "IMPACT": {
                "FUNCTION": enrichment.get("FUNCTION"),
                "PARAMS": enrichment.get("PARAMS", {}),
            }
        }
