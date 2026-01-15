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
    """Extract SOURCE.CONFIG from parsed config."""
    return config["DATA"]["SOURCE"]["CONFIG"]


def get_source_type(config: Dict[str, Any]) -> str:
    """Extract SOURCE.TYPE from parsed config."""
    return config["DATA"]["SOURCE"]["TYPE"]


def get_transform_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract TRANSFORM config from parsed config.

    Config is pre-validated and merged with defaults, so TRANSFORM always exists.
    If ENRICHMENT is configured, automatically injects enrichment_start into PARAMS.
    """
    transform = config["DATA"]["TRANSFORM"]

    # Inject enrichment_start from ENRICHMENT config if present (ENRICHMENT is optional)
    enrichment = config["DATA"].get("ENRICHMENT")
    if enrichment:
        params = enrichment.get("params", {})
        if "enrichment_start" in params:
            transform["PARAMS"]["enrichment_start"] = params["enrichment_start"]

    return transform


def get_measurement_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract MEASUREMENT config from parsed config."""
    return config["MEASUREMENT"]


def get_measurement_params(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract MEASUREMENT.PARAMS from parsed config."""
    return config["MEASUREMENT"]["PARAMS"]
