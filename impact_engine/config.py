"""
Configuration Parser and Validator for Data Abstraction Layer

This module provides configuration parsing and validation functionality
for the data abstraction layer, supporting JSON and YAML formats with
comprehensive error handling and schema validation.
"""

import json
import yaml
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import logging


class ConfigurationError(Exception):
    """
    Exception raised for configuration-related errors.
    
    This exception is used for all configuration parsing and validation
    errors, providing specific error messages for troubleshooting.
    """
    pass


class ConfigurationParser:
    """
    Configuration parser and validator for data abstraction layer.
    
    Handles parsing of JSON and YAML configuration files with comprehensive
    validation of required fields and data types according to the schema
    defined in the design document.
    """
    
    # Required configuration schema
    REQUIRED_SCHEMA = {
        "data_source": {
            "type": str,  # "simulator" or "company_system"
            "connection": dict
        },
        "time_range": {
            "start_date": str,  # ISO format YYYY-MM-DD
            "end_date": str     # ISO format YYYY-MM-DD
        }
    }
    
    # Optional configuration fields
    OPTIONAL_SCHEMA = {
        "metrics": {
            "include": list,
            "aggregation": str
        }
    }
    
    # Valid data source types
    VALID_DATA_SOURCE_TYPES = ["simulator", "company_system"]
    
    # Valid aggregation types
    VALID_AGGREGATION_TYPES = ["daily", "weekly", "monthly"]
    
    def __init__(self):
        """Initialize the configuration parser."""
        self.logger = logging.getLogger(__name__)
    
    def parse_config(self, config_path: str) -> Dict[str, Any]:
        """
        Parse configuration file and validate its contents.
        
        Args:
            config_path: Path to the configuration file (JSON or YAML)
        
        Returns:
            Dict[str, Any]: Parsed and validated configuration
        
        Raises:
            ConfigurationError: If file cannot be parsed or validation fails
            FileNotFoundError: If configuration file does not exist
        """
        config_file = Path(config_path)
        
        # Check if file exists
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        # Parse file based on extension
        try:
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
                        try:
                            config = yaml.safe_load(content)
                        except yaml.YAMLError as e:
                            raise ConfigurationError(
                                f"Unable to parse configuration file as JSON or YAML: {e}"
                            )
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON syntax in configuration file: {e}")
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML syntax in configuration file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error reading configuration file: {e}")
        
        # Validate configuration
        self._validate_config(config)
        
        self.logger.info(f"Successfully parsed and validated configuration from {config_path}")
        return config
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validate configuration against required schema.
        
        Args:
            config: Configuration dictionary to validate
        
        Raises:
            ConfigurationError: If validation fails
        """
        if not isinstance(config, dict):
            raise ConfigurationError("Configuration must be a dictionary/object")
        
        # Validate required sections
        self._validate_required_sections(config)
        
        # Validate data source configuration
        self._validate_data_source_config(config["data_source"])
        
        # Validate time range configuration
        self._validate_time_range_config(config["time_range"])
        
        # Validate optional sections if present
        if "metrics" in config:
            self._validate_metrics_config(config["metrics"])
    
    def _validate_required_sections(self, config: Dict[str, Any]) -> None:
        """Validate that all required sections are present."""
        for section_name, section_schema in self.REQUIRED_SCHEMA.items():
            if section_name not in config:
                raise ConfigurationError(f"Missing required configuration section: {section_name}")
            
            section_config = config[section_name]
            if not isinstance(section_config, dict):
                raise ConfigurationError(f"Configuration section '{section_name}' must be an object")
            
            # Validate required fields in section
            for field_name, field_type in section_schema.items():
                if field_name not in section_config:
                    raise ConfigurationError(
                        f"Missing required field '{field_name}' in section '{section_name}'"
                    )
                
                field_value = section_config[field_name]
                if not isinstance(field_value, field_type):
                    raise ConfigurationError(
                        f"Field '{field_name}' in section '{section_name}' must be of type {field_type.__name__}"
                    )
    
    def _validate_data_source_config(self, data_source_config: Dict[str, Any]) -> None:
        """Validate data source configuration."""
        # Validate data source type
        source_type = data_source_config["type"]
        if source_type not in self.VALID_DATA_SOURCE_TYPES:
            raise ConfigurationError(
                f"Invalid data source type '{source_type}'. "
                f"Valid types: {', '.join(self.VALID_DATA_SOURCE_TYPES)}"
            )
        
        # Validate connection configuration exists
        connection_config = data_source_config["connection"]
        if not isinstance(connection_config, dict):
            raise ConfigurationError("Data source connection configuration must be an object")
        
        # Validate source-specific connection parameters
        if source_type == "simulator":
            self._validate_simulator_connection(connection_config)
        elif source_type == "company_system":
            self._validate_company_system_connection(connection_config)
    
    def _validate_simulator_connection(self, connection_config: Dict[str, Any]) -> None:
        """Validate simulator-specific connection configuration."""
        # Mode is optional, default to "rule"
        if "mode" in connection_config:
            mode = connection_config["mode"]
            if not isinstance(mode, str) or mode not in ["rule", "ml"]:
                raise ConfigurationError(
                    "Simulator mode must be 'rule' or 'ml'"
                )
        
        # Seed is optional
        if "seed" in connection_config:
            seed = connection_config["seed"]
            if not isinstance(seed, int) or seed < 0:
                raise ConfigurationError(
                    "Simulator seed must be a non-negative integer"
                )
    
    def _validate_company_system_connection(self, connection_config: Dict[str, Any]) -> None:
        """Validate company system connection configuration."""
        # Endpoint is required for company systems
        if "endpoint" not in connection_config:
            raise ConfigurationError(
                "Company system connection requires 'endpoint' field"
            )
        
        endpoint = connection_config["endpoint"]
        if not isinstance(endpoint, str) or not endpoint.strip():
            raise ConfigurationError(
                "Company system endpoint must be a non-empty string"
            )
        
        # Auth type is required
        if "auth_type" not in connection_config:
            raise ConfigurationError(
                "Company system connection requires 'auth_type' field"
            )
        
        auth_type = connection_config["auth_type"]
        if auth_type not in ["api_key", "oauth"]:
            raise ConfigurationError(
                "Company system auth_type must be 'api_key' or 'oauth'"
            )
        
        # Credentials are required
        if "credentials" not in connection_config:
            raise ConfigurationError(
                "Company system connection requires 'credentials' field"
            )
        
        if not isinstance(connection_config["credentials"], dict):
            raise ConfigurationError(
                "Company system credentials must be an object"
            )
    
    def _validate_time_range_config(self, time_range_config: Dict[str, Any]) -> None:
        """Validate time range configuration."""
        start_date_str = time_range_config["start_date"]
        end_date_str = time_range_config["end_date"]
        
        # Validate date format
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        except ValueError:
            raise ConfigurationError(
                f"Invalid start_date format '{start_date_str}'. Expected YYYY-MM-DD"
            )
        
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        except ValueError:
            raise ConfigurationError(
                f"Invalid end_date format '{end_date_str}'. Expected YYYY-MM-DD"
            )
        
        # Validate logical consistency
        if start_date > end_date:
            raise ConfigurationError(
                f"start_date ({start_date_str}) must be before or equal to end_date ({end_date_str})"
            )
    
    def _validate_metrics_config(self, metrics_config: Dict[str, Any]) -> None:
        """Validate optional metrics configuration."""
        # Validate include field if present
        if "include" in metrics_config:
            include = metrics_config["include"]
            if not isinstance(include, list):
                raise ConfigurationError("Metrics 'include' field must be a list")
            
            for metric in include:
                if not isinstance(metric, str):
                    raise ConfigurationError("All metrics in 'include' list must be strings")
        
        # Validate aggregation field if present
        if "aggregation" in metrics_config:
            aggregation = metrics_config["aggregation"]
            if not isinstance(aggregation, str):
                raise ConfigurationError("Metrics 'aggregation' field must be a string")
            
            if aggregation not in self.VALID_AGGREGATION_TYPES:
                raise ConfigurationError(
                    f"Invalid aggregation type '{aggregation}'. "
                    f"Valid types: {', '.join(self.VALID_AGGREGATION_TYPES)}"
                )
    
    def create_example_config(self, config_type: str = "simulator") -> Dict[str, Any]:
        """
        Create an example configuration for the specified data source type.
        
        Args:
            config_type: Type of configuration to create ("simulator" or "company_system")
        
        Returns:
            Dict[str, Any]: Example configuration dictionary
        
        Raises:
            ValueError: If config_type is not valid
        """
        if config_type not in self.VALID_DATA_SOURCE_TYPES:
            raise ValueError(f"Invalid config type. Valid types: {self.VALID_DATA_SOURCE_TYPES}")
        
        if config_type == "simulator":
            return {
                "data_source": {
                    "type": "simulator",
                    "connection": {
                        "mode": "rule",
                        "seed": 42
                    }
                },
                "time_range": {
                    "start_date": "2024-11-01",
                    "end_date": "2024-11-30"
                },
                "metrics": {
                    "include": ["sales", "revenue", "inventory"],
                    "aggregation": "daily"
                }
            }
        else:  # company_system
            return {
                "data_source": {
                    "type": "company_system",
                    "connection": {
                        "endpoint": "https://api.company.com",
                        "auth_type": "api_key",
                        "credentials": {
                            "api_key": "your-api-key-here"
                        }
                    }
                },
                "time_range": {
                    "start_date": "2024-11-01",
                    "end_date": "2024-11-30"
                },
                "metrics": {
                    "include": ["sales", "revenue", "inventory"],
                    "aggregation": "daily"
                }
            }


def parse_config_file(config_path: str) -> Dict[str, Any]:
    """
    Convenience function to parse a configuration file.
    
    Args:
        config_path: Path to the configuration file
    
    Returns:
        Dict[str, Any]: Parsed and validated configuration
    
    Raises:
        ConfigurationError: If parsing or validation fails
        FileNotFoundError: If configuration file does not exist
    """
    parser = ConfigurationParser()
    return parser.parse_config(config_path)