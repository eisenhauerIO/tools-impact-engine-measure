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
