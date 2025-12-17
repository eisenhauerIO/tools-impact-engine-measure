"""
Configuration Parser and Validator for Data Abstraction Layer
"""

import json
import yaml
from typing import Dict, Any
from datetime import datetime
from pathlib import Path


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
        with open(config_file, 'r', encoding='utf-8') as f:
            if config_file.suffix.lower() in ['.json']:
                config = json.load(f)
            elif config_file.suffix.lower() in ['.yaml', '.yml']:
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
        if "data_source" not in config:
            raise ConfigurationError("Missing required configuration section: data_source")
        
        if "model" not in config:
            raise ConfigurationError("Missing required configuration section: model")
        
        # Validate data source
        data_source = config["data_source"]
        if "type" not in data_source:
            raise ConfigurationError("Missing required field 'type' in data_source section")
        
        if "connection" not in data_source:
            raise ConfigurationError("Missing required field 'connection' in data_source section")
        
        # Validate model section
        model = config["model"]
        if "time_range" not in model:
            raise ConfigurationError("Missing required field 'time_range' in model section")
        
        # Validate time range
        time_range = model["time_range"]
        if "start_date" not in time_range:
            raise ConfigurationError("Missing required field 'start_date' in model.time_range section")
        
        if "end_date" not in time_range:
            raise ConfigurationError("Missing required field 'end_date' in model.time_range section")
        
        # Validate date format
        try:
            start_date = datetime.strptime(time_range["start_date"], "%Y-%m-%d")
            end_date = datetime.strptime(time_range["end_date"], "%Y-%m-%d")
        except ValueError as e:
            raise ConfigurationError(f"Invalid date format. Expected YYYY-MM-DD: {e}")
        
        # Validate logical consistency
        if start_date > end_date:
            raise ConfigurationError(
                f"start_date ({time_range['start_date']}) must be before or equal to end_date ({time_range['end_date']})"
            )


def parse_config_file(config_path: str) -> Dict[str, Any]:
    """Convenience function to parse a configuration file."""
    parser = ConfigurationParser()
    return parser.parse_config(config_path)