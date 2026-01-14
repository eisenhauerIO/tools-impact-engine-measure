"""
Configuration processing with defaults and validation.

This module provides centralized configuration handling for the impact_engine:
- Load defaults from config_defaults.yaml
- Deep merge user config over defaults
- Validate parameters against expected schemas
- Support custom models/transforms (skip validation for unregistered functions)
"""

import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Set

import yaml


class ConfigurationError(Exception):
    """Exception raised for configuration-related errors."""

    pass


# ---------------------------------------------------------------------------
# Schema extraction from defaults
# ---------------------------------------------------------------------------


def _extract_param_schemas_from_defaults() -> Dict[str, Any]:
    """Extract parameter schemas from config defaults.

    This enables automatic validation of parameters for built-in models.
    Custom models registered at runtime are skipped during validation.
    """
    defaults = load_defaults()
    schemas: Dict[str, Dict[str, Set[str]]] = {}

    # Extract MEASUREMENT model parameter schemas
    if "MEASUREMENT" in defaults and "PARAMS" in defaults["MEASUREMENT"]:
        schemas["MEASUREMENT"] = {}
        params = defaults["MEASUREMENT"]["PARAMS"]

        for model_name, model_params in params.items():
            if isinstance(model_params, dict):
                schemas["MEASUREMENT"][model_name] = set(model_params.keys())

    return schemas


def _get_param_schemas() -> Dict[str, Any]:
    """Get parameter schemas, cached for performance."""
    if not hasattr(_get_param_schemas, "_cache"):
        _get_param_schemas._cache = _extract_param_schemas_from_defaults()
    return _get_param_schemas._cache


# ---------------------------------------------------------------------------
# Default loading and merging
# ---------------------------------------------------------------------------


def load_defaults() -> Dict[str, Any]:
    """Load default configuration from package."""
    defaults_path = Path(__file__).parent / "config_defaults.yaml"
    with open(defaults_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def deep_merge(base: Dict, override: Dict) -> Dict:
    """
    Deep merge two dictionaries, with override values taking precedence.

    Args:
        base: Base dictionary (defaults)
        override: Override dictionary (user config)

    Returns:
        Merged dictionary
    """
    result = copy.deepcopy(base)

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)

    return result


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _require(config: Dict[str, Any], path: str, message: str) -> None:
    """Check that a nested path exists and is not null/empty.

    Args:
        config: Configuration dictionary
        path: Dot-separated path (e.g., "DATA.SOURCE.TYPE")
        message: Error message if validation fails

    Raises:
        ConfigurationError: If the required field is missing or empty
    """
    parts = path.split(".")
    cur: Any = config
    for part in parts:
        if not isinstance(cur, dict) or part not in cur or cur[part] in (None, ""):
            raise ConfigurationError(message)
        cur = cur[part]


def _validate_date_format(date_str: str, field_name: str) -> datetime:
    """Validate date string format (YYYY-MM-DD).

    Args:
        date_str: Date string to validate
        field_name: Field name for error messages

    Returns:
        Parsed datetime object

    Raises:
        ConfigurationError: If date format is invalid
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        raise ConfigurationError(
            f"Invalid {field_name} format. Expected YYYY-MM-DD: {e}"
        )


def _validate_model_params(
    model_name: str, params: Dict[str, Any], required_non_null: Optional[Set[str]] = None
) -> None:
    """Validate parameters against expected schema for built-in models.

    For built-in models defined in config_defaults.yaml, this performs strict
    parameter validation to catch configuration errors early (typos, missing params, etc.).

    For custom models registered via register_model_adapter(), validation is skipped
    since their parameter schemas are not known at config processing time.

    Args:
        model_name: Name of the model (e.g., "interrupted_time_series")
        params: Parameters to validate
        required_non_null: Set of param names that cannot be null

    Raises:
        ConfigurationError: If validation fails
    """
    schemas = _get_param_schemas()

    if "MEASUREMENT" not in schemas:
        return

    if model_name not in schemas["MEASUREMENT"]:
        # Custom model - skip validation, trust the registry and runtime
        return

    expected_params = schemas["MEASUREMENT"][model_name]
    provided_params = set(params.keys())

    # Check for unexpected parameters
    extra_params = provided_params - expected_params
    if extra_params:
        raise ConfigurationError(
            f"Unexpected parameters for model '{model_name}': "
            f"{sorted(extra_params)}. Expected: {sorted(expected_params)}"
        )

    # Check for null values that must be user-provided
    if required_non_null:
        for param in required_non_null:
            if param in params and params[param] is None:
                raise ConfigurationError(
                    f"Parameter '{param}' for model '{model_name}' must be provided by user (cannot be null)"
                )


# ---------------------------------------------------------------------------
# Main validation
# ---------------------------------------------------------------------------


def validate_config(config: Dict[str, Any]) -> None:
    """Validate configuration has required fields and valid parameters.

    Args:
        config: Merged configuration dictionary

    Raises:
        ConfigurationError: If validation fails
    """
    # Validate required top-level sections
    _require(config, "DATA", "Missing required configuration section: DATA")
    _require(config, "MEASUREMENT", "Missing required configuration section: MEASUREMENT")

    # Validate DATA section
    _validate_data_section(config["DATA"])

    # Validate MEASUREMENT section
    _validate_measurement_section(config["MEASUREMENT"])


def _validate_data_section(data: Dict[str, Any]) -> None:
    """Validate DATA section with SOURCE and TRANSFORM."""
    _require(data, "SOURCE", "Missing required field 'SOURCE' in DATA section")
    _require(data, "SOURCE.TYPE", "Missing required field 'TYPE' in DATA.SOURCE section")
    _require(data, "SOURCE.CONFIG", "Missing required field 'CONFIG' in DATA.SOURCE section")

    source_config = data["SOURCE"]["CONFIG"]

    # Validate required fields in SOURCE.CONFIG
    _require(
        data,
        "SOURCE.CONFIG.PATH",
        "Missing required field 'PATH' in DATA.SOURCE.CONFIG section",
    )
    _require(
        data,
        "SOURCE.CONFIG.START_DATE",
        "Missing required field 'START_DATE' in DATA.SOURCE.CONFIG section",
    )
    _require(
        data,
        "SOURCE.CONFIG.END_DATE",
        "Missing required field 'END_DATE' in DATA.SOURCE.CONFIG section",
    )

    # Validate date formats
    start_date = _validate_date_format(source_config["START_DATE"], "START_DATE")
    end_date = _validate_date_format(source_config["END_DATE"], "END_DATE")

    # Validate date consistency
    if start_date > end_date:
        raise ConfigurationError(
            f"DATA.SOURCE.CONFIG START_DATE ({source_config['START_DATE']}) "
            f"must be before or equal to END_DATE ({source_config['END_DATE']})"
        )

    # Validate TRANSFORM section if present
    if "TRANSFORM" in data:
        _validate_transform_section(data["TRANSFORM"])


def _validate_transform_section(transform: Dict[str, Any]) -> None:
    """Validate TRANSFORM section."""
    if "FUNCTION" not in transform:
        raise ConfigurationError(
            "Missing required field 'FUNCTION' in DATA.TRANSFORM section"
        )


def _validate_measurement_section(measurement: Dict[str, Any]) -> None:
    """Validate MEASUREMENT section."""
    _require(measurement, "MODEL", "Missing required field 'MODEL' in MEASUREMENT section")
    _require(measurement, "PARAMS", "Missing required field 'PARAMS' in MEASUREMENT section")

    model = measurement["MODEL"]
    params = measurement["PARAMS"]

    # Model-specific parameter validation
    if model == "interrupted_time_series":
        _validate_model_params(
            model, params, required_non_null={"intervention_date"}
        )
        # Validate intervention date format if provided
        if "intervention_date" in params and params["intervention_date"]:
            _validate_date_format(params["intervention_date"], "intervention_date")

    elif model == "metrics_approximation":
        _validate_model_params(model, params)
    else:
        # Custom model - validate_params will handle validation at runtime
        pass


# ---------------------------------------------------------------------------
# Model-specific defaults application
# ---------------------------------------------------------------------------


def _apply_model_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply model-specific defaults to MEASUREMENT.PARAMS.

    This extracts the appropriate defaults based on the selected model type
    and merges them with user-provided params.

    Args:
        config: Configuration with MEASUREMENT section

    Returns:
        Configuration with model-specific defaults applied
    """
    defaults = load_defaults()
    result = copy.deepcopy(config)

    model = result.get("MEASUREMENT", {}).get("MODEL")
    user_params = result.get("MEASUREMENT", {}).get("PARAMS", {})

    # Get model-specific defaults
    model_defaults = (
        defaults.get("MEASUREMENT", {}).get("PARAMS", {}).get(model, {})
    )

    if model_defaults:
        # Deep merge user params over model defaults
        merged_params = deep_merge(model_defaults, user_params)
        result["MEASUREMENT"]["PARAMS"] = merged_params

    # Convert list params to tuples where expected (YAML loads lists, not tuples)
    result = _convert_list_params_to_tuples(result)

    return result


def _convert_list_params_to_tuples(config: Dict[str, Any]) -> Dict[str, Any]:
    """Convert list parameters to tuples where expected by adapters.

    YAML loads sequences as Python lists, but some adapters (like ITS)
    expect tuples for certain parameters.

    Args:
        config: Configuration dictionary

    Returns:
        Configuration with converted parameters
    """
    result = copy.deepcopy(config)
    model = result.get("MEASUREMENT", {}).get("MODEL")
    params = result.get("MEASUREMENT", {}).get("PARAMS", {})

    if model == "interrupted_time_series":
        if "order" in params and isinstance(params["order"], list):
            params["order"] = tuple(params["order"])
        if "seasonal_order" in params and isinstance(params["seasonal_order"], list):
            params["seasonal_order"] = tuple(params["seasonal_order"])

    return result


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def process_config(config_path: str) -> Dict[str, Any]:
    """
    Load, merge with defaults, and validate configuration.

    This is the main entry point for configuration processing. It:
    1. Loads the user configuration file
    2. Loads defaults from config_defaults.yaml
    3. Deep merges user config over defaults
    4. Applies model-specific parameter defaults
    5. Validates the merged configuration

    Args:
        config_path: Path to user configuration file (local path)

    Returns:
        Complete validated configuration

    Raises:
        FileNotFoundError: If config file doesn't exist
        ConfigurationError: If configuration is invalid
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    # Load user config
    with open(config_file, "r", encoding="utf-8") as f:
        if config_file.suffix.lower() in [".json"]:
            user_config = json.load(f)
        elif config_file.suffix.lower() in [".yaml", ".yml"]:
            user_config = yaml.safe_load(f)
        else:
            # Try JSON first, then YAML
            content = f.read()
            try:
                user_config = json.loads(content)
            except json.JSONDecodeError:
                user_config = yaml.safe_load(content)

    # Load defaults
    defaults = load_defaults()

    # Remove model-specific param blocks from defaults (they're handled separately)
    defaults_copy = copy.deepcopy(defaults)
    if "MEASUREMENT" in defaults_copy and "PARAMS" in defaults_copy["MEASUREMENT"]:
        # Clear the nested model params - they'll be applied per-model
        defaults_copy["MEASUREMENT"]["PARAMS"] = {}

    # Deep merge user config over defaults
    config = deep_merge(defaults_copy, user_config)

    # Apply model-specific defaults
    config = _apply_model_defaults(config)

    # Inject enrichment_start into transform params if present
    config = _inject_enrichment_params(config)

    # Validate
    validate_config(config)

    return config


def _inject_enrichment_params(config: Dict[str, Any]) -> Dict[str, Any]:
    """Inject enrichment parameters into transform config.

    If ENRICHMENT is configured, automatically injects enrichment_start into
    TRANSFORM.PARAMS for transforms that need it.

    Args:
        config: Configuration dictionary

    Returns:
        Configuration with enrichment params injected
    """
    result = copy.deepcopy(config)

    enrichment = result.get("DATA", {}).get("ENRICHMENT")
    if enrichment:
        params = enrichment.get("params", {})
        if "enrichment_start" in params:
            transform = result.get("DATA", {}).get("TRANSFORM", {})
            if "PARAMS" not in transform:
                transform["PARAMS"] = {}
            transform["PARAMS"]["enrichment_start"] = params["enrichment_start"]
            result["DATA"]["TRANSFORM"] = transform

    return result


# ---------------------------------------------------------------------------
# Legacy ConfigurationParser for backward compatibility
# ---------------------------------------------------------------------------


class ConfigurationParser:
    """Configuration parser and validator for data abstraction layer.

    Note: For new code, prefer using process_config() directly.
    This class is maintained for backward compatibility.
    """

    def parse_config(self, config_path: str) -> Dict[str, Any]:
        """Parse configuration file and validate its contents.

        This method now delegates to process_config() for centralized handling.
        """
        return process_config(config_path)


def parse_config_file(config_path: str) -> Dict[str, Any]:
    """Convenience function to parse a configuration file.

    Delegates to process_config() for centralized handling.
    """
    return process_config(config_path)


# ---------------------------------------------------------------------------
# Helper functions for extracting config parts
# ---------------------------------------------------------------------------


def get_source_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract SOURCE.CONFIG from parsed config."""
    return config["DATA"]["SOURCE"]["CONFIG"]


def get_source_type(config: Dict[str, Any]) -> str:
    """Extract SOURCE.TYPE from parsed config."""
    return config["DATA"]["SOURCE"]["TYPE"]


def get_transform_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract TRANSFORM config from parsed config, or default passthrough.

    Note: If using process_config(), enrichment params are already injected.
    """
    return config["DATA"].get("TRANSFORM", {"FUNCTION": "passthrough", "PARAMS": {}})


def get_measurement_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract MEASUREMENT config from parsed config."""
    return config["MEASUREMENT"]


def get_measurement_params(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract MEASUREMENT.PARAMS from parsed config."""
    return config["MEASUREMENT"]["PARAMS"]


def get_enrichment_config(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract ENRICHMENT config from parsed config, if present."""
    return config.get("DATA", {}).get("ENRICHMENT")


def get_output_path(config: Dict[str, Any]) -> str:
    """Extract OUTPUT.PATH from parsed config, with default."""
    return config.get("OUTPUT", {}).get("PATH", "output")
