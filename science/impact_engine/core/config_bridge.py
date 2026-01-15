"""
Configuration bridge for translating between impact-engine and external systems.

This module provides bidirectional translation between configuration schemas,
ensuring libraries communicate only through well-defined config formats.
"""

from typing import Any, Dict

# Default simulation parameters for catalog simulator
DEFAULT_SALE_PROB = 0.7
DEFAULT_IMPRESSION_TO_VISIT_RATE = 0.15
DEFAULT_VISIT_TO_CART_RATE = 0.25
DEFAULT_CART_TO_ORDER_RATE = 0.80


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

        Example input (impact-engine format):
            DATA:
              TYPE: simulator
              MODE: rule
              SEED: 42
              START_DATE: "2024-01-01"
              END_DATE: "2024-01-31"
              ENRICHMENT:
                FUNCTION: quantity_boost
                PARAMS:
                  effect_size: 0.3
                  enrichment_start: "2024-01-15"

        Example output (catalog-simulator format):
            RULE:
              CHARACTERISTICS:
                FUNCTION: simulate_characteristics_rule_based
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

        # Build RULE config
        cs_config: Dict[str, Any] = {
            "RULE": {
                "CHARACTERISTICS": {
                    "FUNCTION": "simulate_characteristics_rule_based",
                    "PARAMS": {"num_products": num_products, "seed": seed},
                },
                "METRICS": {
                    "FUNCTION": "simulate_metrics_rule_based",
                    "PARAMS": {
                        "date_start": data.get("start_date"),
                        "date_end": data.get("end_date"),
                        "seed": seed,
                        "sale_prob": DEFAULT_SALE_PROB,
                        "granularity": "daily",
                        "impression_to_visit_rate": DEFAULT_IMPRESSION_TO_VISIT_RATE,
                        "visit_to_cart_rate": DEFAULT_VISIT_TO_CART_RATE,
                        "cart_to_order_rate": DEFAULT_CART_TO_ORDER_RATE,
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
