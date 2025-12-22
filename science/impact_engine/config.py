"""
Configuration Parser and Validator for Data Abstraction Layer
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

        # Validate data section
        data = config["DATA"]
        if "TYPE" not in data:
            raise ConfigurationError("Missing required field 'TYPE' in DATA section")

        if "PATH" not in data:
            raise ConfigurationError("Missing required field 'PATH' in DATA section")

        if "START_DATE" not in data:
            raise ConfigurationError("Missing required field 'START_DATE' in DATA section")

        if "END_DATE" not in data:
            raise ConfigurationError("Missing required field 'END_DATE' in DATA section")

        # Validate DATA section date format
        try:
            data_start_date = datetime.strptime(data["START_DATE"], "%Y-%m-%d")
            data_end_date = datetime.strptime(data["END_DATE"], "%Y-%m-%d")
        except ValueError as e:
            raise ConfigurationError(
                f"Invalid date format in DATA section. Expected YYYY-MM-DD: {e}"
            )

        # Validate DATA section date consistency
        if data_start_date > data_end_date:
            raise ConfigurationError(
                f"DATA START_DATE ({data['START_DATE']}) must be before or equal to END_DATE ({data['END_DATE']})"
            )

        # Validate measurement section
        measurement = config["MEASUREMENT"]
        if "MODEL" not in measurement:
            raise ConfigurationError("Missing required field 'MODEL' in MEASUREMENT section")

        if "PARAMS" not in measurement:
            raise ConfigurationError("Missing required field 'PARAMS' in MEASUREMENT section")

        # Validate measurement params
        params = measurement["PARAMS"]
        if "INTERVENTION_DATE" not in params:
            raise ConfigurationError(
                "Missing required field 'INTERVENTION_DATE' in MEASUREMENT.PARAMS section"
            )

        # Validate intervention date format
        try:
            datetime.strptime(params["INTERVENTION_DATE"], "%Y-%m-%d")
        except ValueError as e:
            raise ConfigurationError(f"Invalid INTERVENTION_DATE format. Expected YYYY-MM-DD: {e}")


def parse_config_file(config_path: str) -> Dict[str, Any]:
    """Convenience function to parse a configuration file."""
    parser = ConfigurationParser()
    return parser.parse_config(config_path)
