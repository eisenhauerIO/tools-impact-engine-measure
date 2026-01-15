"""
Configuration Parser and Validator for Data Abstraction Layer

Delegates to centralized validation in core.validation module.
"""

from typing import Any, Dict

from .core.validation import ConfigValidationError, process_config


class ConfigurationError(ConfigValidationError):
    """Exception raised for configuration-related errors.

    Inherits from ConfigValidationError for backward compatibility.
    """

    pass


class ConfigurationParser:
    """Configuration parser and validator for data abstraction layer.

    Delegates to centralized process_config() for validation and default merging.
    """

    def parse_config(self, config_path: str) -> Dict[str, Any]:
        """Parse configuration file and validate its contents.

        Uses centralized validation which:
        - Merges user config with defaults from config_defaults.yaml
        - Validates structure and required fields
        - Validates date formats and parameter values

        Args:
            config_path: Path to the configuration file (YAML or JSON).

        Returns:
            Fully validated and merged configuration dictionary.

        Raises:
            ConfigurationError: If validation fails.
        """
        try:
            return process_config(config_path)
        except ConfigValidationError as e:
            raise ConfigurationError(str(e)) from e


def parse_config_file(config_path: str) -> Dict[str, Any]:
    """Convenience function to parse a configuration file."""
    parser = ConfigurationParser()
    return parser.parse_config(config_path)


# Helper functions for extracting config parts
def get_source_config(config: Dict[str, Any]) -> Dict[str, Any]:
    return config["DATA"]["SOURCE"]["CONFIG"]


def get_source_type(config: Dict[str, Any]) -> str:
    return config["DATA"]["SOURCE"]["type"]


def get_transform_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Injects enrichment_start into PARAMS if ENRICHMENT is configured."""
    transform = config["DATA"]["TRANSFORM"]

    enrichment = config["DATA"].get("ENRICHMENT")
    if enrichment:
        params = enrichment.get("PARAMS", {})
        if "enrichment_start" in params:
            transform["PARAMS"]["enrichment_start"] = params["enrichment_start"]

    return transform


def get_measurement_config(config: Dict[str, Any]) -> Dict[str, Any]:
    return config["MEASUREMENT"]


def get_measurement_params(config: Dict[str, Any]) -> Dict[str, Any]:
    return config["MEASUREMENT"]["PARAMS"]
