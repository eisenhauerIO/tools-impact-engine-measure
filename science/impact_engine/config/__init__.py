"""
Configuration module for impact_engine.

Provides configuration parsing, validation, and helper functions.
"""

from .parser import (
    ConfigurationError,
    ConfigurationParser,
    get_measurement_config,
    get_measurement_params,
    get_source_config,
    get_source_type,
    get_transform_config,
    parse_config_file,
)
from .validators import (
    ConfigError,
    ConfigValidator,
    DataSourceValidator,
    ITSParamsValidator,
    MeasurementValidator,
    MetricsApproximationParamsValidator,
    TransformValidator,
    get_validator,
    list_validators,
    register_validator,
    validate_config_with_validators,
)

__all__ = [
    # Parser exports
    "ConfigurationError",
    "ConfigurationParser",
    "parse_config_file",
    "get_source_config",
    "get_source_type",
    "get_transform_config",
    "get_measurement_config",
    "get_measurement_params",
    # Validator exports
    "ConfigError",
    "ConfigValidator",
    "DataSourceValidator",
    "ITSParamsValidator",
    "MeasurementValidator",
    "MetricsApproximationParamsValidator",
    "TransformValidator",
    "get_validator",
    "list_validators",
    "register_validator",
    "validate_config_with_validators",
]
