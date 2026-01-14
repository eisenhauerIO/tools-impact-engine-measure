"""
Configuration Parser and Validator for Data Abstraction Layer

Supports the new two-level DATA structure with SOURCE and TRANSFORM sections.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import yaml


class ConfigurationError(Exception):
    """Exception raised for configuration-related errors."""

    pass


class ConfigurationParser:
    """Configuration parser and validator for data abstraction layer."""

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

        # Basic validation
        self._validate_config(config)
        return config

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration against required schema."""
        if not isinstance(config, dict):
            raise ConfigurationError("Configuration must be a dictionary/object")

        # Check required sections
        if "DATA" not in config:
            raise ConfigurationError("Missing required configuration section: DATA")

        if "MEASUREMENT" not in config:
            raise ConfigurationError("Missing required configuration section: MEASUREMENT")

        # Validate DATA section
        self._validate_data_section(config["DATA"])

        # Validate MEASUREMENT section
        self._validate_measurement_section(config["MEASUREMENT"])

    def _validate_data_section(self, data: Dict[str, Any]) -> None:
        """Validate DATA section with SOURCE and TRANSFORM."""
        if "SOURCE" not in data:
            raise ConfigurationError("Missing required field 'SOURCE' in DATA section")

        source = data["SOURCE"]

        if "TYPE" not in source:
            raise ConfigurationError("Missing required field 'TYPE' in DATA.SOURCE section")

        if "CONFIG" not in source:
            raise ConfigurationError("Missing required field 'CONFIG' in DATA.SOURCE section")

        source_config = source["CONFIG"]

        # Validate required fields in SOURCE.CONFIG
        if "PATH" not in source_config:
            raise ConfigurationError("Missing required field 'PATH' in DATA.SOURCE.CONFIG section")

        if "START_DATE" not in source_config:
            raise ConfigurationError(
                "Missing required field 'START_DATE' in DATA.SOURCE.CONFIG section"
            )

        if "END_DATE" not in source_config:
            raise ConfigurationError(
                "Missing required field 'END_DATE' in DATA.SOURCE.CONFIG section"
            )

        # Validate date format
        try:
            start_date = datetime.strptime(source_config["START_DATE"], "%Y-%m-%d")
            end_date = datetime.strptime(source_config["END_DATE"], "%Y-%m-%d")
        except ValueError as e:
            raise ConfigurationError(
                f"Invalid date format in DATA.SOURCE.CONFIG. Expected YYYY-MM-DD: {e}"
            )

        # Validate date consistency
        if start_date > end_date:
            raise ConfigurationError(
                f"DATA.SOURCE.CONFIG START_DATE ({source_config['START_DATE']}) "
                f"must be before or equal to END_DATE ({source_config['END_DATE']})"
            )

        # Validate TRANSFORM section if present
        if "TRANSFORM" in data:
            self._validate_transform_section(data["TRANSFORM"])

    def _validate_transform_section(self, transform: Dict[str, Any]) -> None:
        """Validate TRANSFORM section."""
        if "FUNCTION" not in transform:
            raise ConfigurationError(
                "Missing required field 'FUNCTION' in DATA.TRANSFORM section"
            )

    def _validate_measurement_section(self, measurement: Dict[str, Any]) -> None:
        """Validate MEASUREMENT section."""
        if "MODEL" not in measurement:
            raise ConfigurationError("Missing required field 'MODEL' in MEASUREMENT section")

        if "PARAMS" not in measurement:
            raise ConfigurationError("Missing required field 'PARAMS' in MEASUREMENT section")

        # Model-specific parameter validation
        model = measurement["MODEL"]
        params = measurement["PARAMS"]

        if model == "interrupted_time_series":
            self._validate_its_params(params)
        elif model == "metrics_approximation":
            self._validate_approximation_params(params)

    def _validate_its_params(self, params: Dict[str, Any]) -> None:
        """Validate ITS model parameters."""
        if "intervention_date" not in params:
            raise ConfigurationError(
                "Missing required field 'intervention_date' in MEASUREMENT.PARAMS "
                "for interrupted_time_series model"
            )

        # Validate intervention date format
        try:
            datetime.strptime(params["intervention_date"], "%Y-%m-%d")
        except ValueError as e:
            raise ConfigurationError(
                f"Invalid intervention_date format. Expected YYYY-MM-DD: {e}"
            )

    def _validate_approximation_params(self, params: Dict[str, Any]) -> None:
        """Validate metrics approximation model parameters."""
        # Metrics approximation has optional params, no required fields
        pass


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
    """Extract TRANSFORM config from parsed config, or default passthrough."""
    return config["DATA"].get("TRANSFORM", {"FUNCTION": "passthrough", "PARAMS": {}})


def get_measurement_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract MEASUREMENT config from parsed config."""
    return config["MEASUREMENT"]


def get_measurement_params(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract MEASUREMENT.PARAMS from parsed config."""
    return config["MEASUREMENT"]["PARAMS"]
