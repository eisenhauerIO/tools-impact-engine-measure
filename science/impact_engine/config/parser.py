"""
Configuration Parser and Validator for Data Abstraction Layer

Supports the new two-level DATA structure with SOURCE and TRANSFORM sections.

This module provides two validation approaches:
1. Legacy validation via ConfigurationParser (backward compatible)
2. Pluggable validators via config.validators module (extensible)

For new code, prefer using the pluggable validators for extensibility.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .validators import (
    ConfigError,
    validate_config_with_validators,
)


class ConfigurationError(Exception):
    """Exception raised for configuration-related errors."""

    def __init__(self, message: str, errors: Optional[List] = None):
        super().__init__(message)
        self.errors = errors or []

    def __str__(self) -> str:
        if self.errors:
            error_list = "\n  - ".join(str(e) for e in self.errors)
            return f"{self.args[0]}\n  - {error_list}"
        return self.args[0]


class ConfigurationParser:
    """Configuration parser and validator for data abstraction layer.

    This parser supports both legacy validation (for backward compatibility)
    and pluggable validators (for extensibility).

    By default, uses pluggable validators if available. Set use_legacy_validation=True
    for backward compatible behavior.
    """

    def __init__(self, use_legacy_validation: bool = False):
        """Initialize the parser.

        Args:
            use_legacy_validation: If True, use legacy hard-coded validation.
                                   If False (default), use pluggable validators.
        """
        self.use_legacy_validation = use_legacy_validation

    def parse_config(self, config_path: str) -> Dict[str, Any]:
        """Parse configuration file and validate its contents."""
        config_file = Path(config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        # Parse file based on extension
        with open(config_file, "r", encoding="utf-8") as f:
            if config_file.suffix.lower() in [".json"]:
                config = json.load(f)
            elif config_file.suffix.lower() in [".yaml", ".yml"]:
                config = yaml.safe_load(f)
            else:
                # Try JSON first, then YAML
                content = f.read()
                try:
                    config = json.loads(content)
                except json.JSONDecodeError:
                    config = yaml.safe_load(content)

        # Validate using selected approach
        if self.use_legacy_validation:
            self._validate_config_legacy(config)
        else:
            self._validate_config_pluggable(config)

        return config

    def _validate_config_pluggable(self, config: Dict[str, Any]) -> None:
        """Validate configuration using pluggable validators."""
        if not isinstance(config, dict):
            raise ConfigurationError("Configuration must be a dictionary/object")

        errors = validate_config_with_validators(config)
        if errors:
            raise ConfigurationError(
                f"Configuration validation failed with {len(errors)} error(s)",
                errors=errors,
            )

    def _validate_config_legacy(self, config: Dict[str, Any]) -> None:
        """Legacy validation for backward compatibility."""
        if not isinstance(config, dict):
            raise ConfigurationError("Configuration must be a dictionary/object")

        # Check required sections
        if "DATA" not in config:
            raise ConfigurationError("Missing required configuration section: DATA")

        if "MEASUREMENT" not in config:
            raise ConfigurationError("Missing required configuration section: MEASUREMENT")

        # Validate DATA section
        data = config["DATA"]
        if "SOURCE" not in data:
            raise ConfigurationError("Missing required field 'SOURCE' in DATA section")

        source = data["SOURCE"]
        if "TYPE" not in source:
            raise ConfigurationError("Missing required field 'TYPE' in DATA.SOURCE section")
        if "CONFIG" not in source:
            raise ConfigurationError("Missing required field 'CONFIG' in DATA.SOURCE section")

        source_config = source["CONFIG"]
        for field in ["PATH", "START_DATE", "END_DATE"]:
            if field not in source_config:
                raise ConfigurationError(
                    f"Missing required field '{field}' in DATA.SOURCE.CONFIG section"
                )

        # Validate dates
        try:
            start_date = datetime.strptime(source_config["START_DATE"], "%Y-%m-%d")
            end_date = datetime.strptime(source_config["END_DATE"], "%Y-%m-%d")
        except ValueError as e:
            raise ConfigurationError(
                f"Invalid date format in DATA.SOURCE.CONFIG. Expected YYYY-MM-DD: {e}"
            )

        if start_date > end_date:
            raise ConfigurationError(
                f"DATA.SOURCE.CONFIG START_DATE ({source_config['START_DATE']}) "
                f"must be before or equal to END_DATE ({source_config['END_DATE']})"
            )

        # Validate TRANSFORM if present
        if "TRANSFORM" in data and "FUNCTION" not in data["TRANSFORM"]:
            raise ConfigurationError(
                "Missing required field 'FUNCTION' in DATA.TRANSFORM section"
            )

        # Validate MEASUREMENT section
        measurement = config["MEASUREMENT"]
        if "MODEL" not in measurement:
            raise ConfigurationError("Missing required field 'MODEL' in MEASUREMENT section")
        if "PARAMS" not in measurement:
            raise ConfigurationError("Missing required field 'PARAMS' in MEASUREMENT section")

        # Model-specific validation
        model = measurement["MODEL"]
        params = measurement["PARAMS"]

        if model == "interrupted_time_series":
            if "intervention_date" not in params:
                raise ConfigurationError(
                    "Missing required field 'intervention_date' in MEASUREMENT.PARAMS "
                    "for interrupted_time_series model"
                )
            try:
                datetime.strptime(params["intervention_date"], "%Y-%m-%d")
            except ValueError as e:
                raise ConfigurationError(
                    f"Invalid intervention_date format. Expected YYYY-MM-DD: {e}"
                )


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
    """Extract TRANSFORM config from parsed config, or default passthrough.

    If ENRICHMENT is configured, automatically injects enrichment_start into PARAMS.
    """
    transform = config["DATA"].get("TRANSFORM", {"FUNCTION": "passthrough", "PARAMS": {}})

    # Ensure PARAMS exists
    if "PARAMS" not in transform:
        transform["PARAMS"] = {}

    # Inject enrichment_start from ENRICHMENT config if present
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
