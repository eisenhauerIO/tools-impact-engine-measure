"""
Centralized configuration validation for impact-engine.

Provides a single entry point for config processing:
    load -> merge defaults -> validate structure -> validate parameters

Design principles:
- Schema derived from config_defaults.yaml (null values = required fields)
  Why: Single source of truth - no duplicate schema definitions
- Deep merge of user config over defaults
  Why: Users specify only what differs from defaults
- Skip param validation for unknown/custom functions
  Why: Enables extensibility without modifying validation code;
  custom adapters validate via their own validate_params() method
- Fail early with descriptive error messages
  Why: Catch config errors before expensive operations begin
"""

import copy
import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml


class ConfigValidationError(ValueError):
    """Exception raised for configuration validation errors."""

    def __init__(self, message: str, path: Optional[str] = None):
        self.path = path
        context = f" at '{path}'" if path else ""
        super().__init__(f"{message}{context}")


# --- Defaults Loading ---


@lru_cache(maxsize=1)
def get_defaults() -> Dict[str, Any]:
    """Load and cache config_defaults.yaml.

    Returns:
        Dict containing all default values.
    """
    defaults_path = Path(__file__).parent.parent / "config_defaults.yaml"
    if not defaults_path.exists():
        return {}

    with open(defaults_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_known_functions() -> Dict[str, Set[str]]:
    """Extract known function names from defaults for each section.

    Returns:
        Dict mapping section names to sets of known function names.
        Example: {"TRANSFORM": {"passthrough", "aggregate_by_date"}}
    """
    defaults = get_defaults()
    known = {}

    # TRANSFORM functions
    transform = defaults.get("DATA", {}).get("TRANSFORM", {})
    if "FUNCTION" in transform:
        known["TRANSFORM"] = {transform["FUNCTION"]}

    # MEASUREMENT models
    measurement = defaults.get("MEASUREMENT", {})
    if "MODEL" in measurement:
        known["MODEL"] = {measurement["MODEL"]}

    return known


# --- Deep Merge ---


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries, with override taking precedence.

    Args:
        base: Base dictionary (typically defaults).
        override: Override dictionary (typically user config).

    Returns:
        Merged dictionary.
    """
    result = copy.deepcopy(base)

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)

    return result


# --- Validation Pipeline ---


def _validate_file(config_path: str) -> str:
    """Stage 1: Validate file exists and is readable.

    Args:
        config_path: Path to configuration file.

    Returns:
        Absolute path to file.

    Raises:
        ConfigValidationError: If file doesn't exist.
    """
    path = Path(config_path)

    if not path.exists():
        raise ConfigValidationError(f"Configuration file not found: {config_path}")

    if not path.is_file():
        raise ConfigValidationError(f"Path is not a file: {config_path}")

    return str(path.absolute())


def _validate_format(config_path: str) -> Dict[str, Any]:
    """Stage 2: Parse file and validate it's proper YAML/JSON.

    Args:
        config_path: Path to configuration file.

    Returns:
        Parsed configuration dictionary.

    Raises:
        ConfigValidationError: If file can't be parsed.
    """
    path = Path(config_path)

    try:
        with open(path, "r", encoding="utf-8") as f:
            if path.suffix.lower() in [".json"]:
                return json.load(f)
            elif path.suffix.lower() in [".yaml", ".yml"]:
                return yaml.safe_load(f) or {}
            else:
                # Try JSON first, then YAML
                content = f.read()
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return yaml.safe_load(content) or {}
    except Exception as e:
        raise ConfigValidationError(f"Failed to parse configuration file: {e}")


def _validate_structure(config: Dict[str, Any]) -> List[str]:
    """Stage 3: Validate required top-level structure.

    Args:
        config: Configuration dictionary to validate.

    Returns:
        List of validation errors (empty if valid).
    """
    errors = []

    # Required top-level sections
    if "DATA" not in config:
        errors.append("Missing required section: DATA")

    if "MEASUREMENT" not in config:
        errors.append("Missing required section: MEASUREMENT")

    # DATA.SOURCE structure
    data = config.get("DATA", {})
    if "SOURCE" not in data:
        errors.append("Missing required field: DATA.SOURCE")
    else:
        source = data["SOURCE"]
        if "type" not in source:
            errors.append("Missing required field: DATA.SOURCE.type")
        if "CONFIG" not in source:
            errors.append("Missing required field: DATA.SOURCE.CONFIG")
        else:
            source_config = source["CONFIG"]
            source_type = source.get("type", "simulator").lower()

            # Required fields depend on source type
            if source_type == "file":
                # File source only needs path
                required_fields = ["path"]
            else:
                # Simulator source needs path, start_date, end_date
                required_fields = ["path", "start_date", "end_date"]

            for field in required_fields:
                if field not in source_config or source_config[field] is None:
                    errors.append(f"Missing required field: DATA.SOURCE.CONFIG.{field}")

    # MEASUREMENT structure
    measurement = config.get("MEASUREMENT", {})
    if "MODEL" not in measurement:
        errors.append("Missing required field: MEASUREMENT.MODEL")
    if "PARAMS" not in measurement:
        errors.append("Missing required field: MEASUREMENT.PARAMS")

    return errors


def _validate_parameters(config: Dict[str, Any]) -> List[str]:
    """Stage 4: Validate parameter values and relationships.

    Validates:
    - Date formats (YYYY-MM-DD)
    - Date ordering (start <= end)
    - Model-specific required params (for known models only)

    Args:
        config: Merged configuration dictionary.

    Returns:
        List of validation errors (empty if valid).
    """
    errors = []

    # Date validation for SOURCE.CONFIG
    source_config = config.get("DATA", {}).get("SOURCE", {}).get("CONFIG", {})

    start_date_str = source_config.get("start_date")
    end_date_str = source_config.get("end_date")

    start_date = None
    end_date = None

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        except ValueError:
            errors.append(
                f"Invalid date format for DATA.SOURCE.CONFIG.start_date: '{start_date_str}'. Expected YYYY-MM-DD"
            )

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        except ValueError:
            errors.append(f"Invalid date format for DATA.SOURCE.CONFIG.end_date: '{end_date_str}'. Expected YYYY-MM-DD")

    if start_date and end_date and start_date > end_date:
        errors.append(
            f"DATA.SOURCE.CONFIG.start_date ({start_date_str}) must be before or equal to end_date ({end_date_str})"
        )

    return errors


# --- Main Entry Point ---


def load_config(source: str | Path | Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Canonical entry point. Accepts file path, dict, or None (returns defaults).

    Parameters
    ----------
    source : str | Path | dict | None
        YAML/JSON file path, pre-parsed dict, or ``None`` for pure defaults.
        When a dict is supplied, file-loading stages are skipped.

    Returns
    -------
    dict
        Fully validated and merged configuration.

    Raises
    ------
    ConfigValidationError
        If validation fails. Note: ``None`` source returns default values but
        required fields (``path``, ``start_date``, etc.) will still fail validation.
    """
    if source is None or isinstance(source, dict):
        user_config: Dict[str, Any] = source or {}
        defaults = get_defaults()
        merged = deep_merge(defaults, user_config)
        structure_errors = _validate_structure(merged)
        if structure_errors:
            raise ConfigValidationError("Configuration structure errors:\n  - " + "\n  - ".join(structure_errors))
        param_errors = _validate_parameters(merged)
        if param_errors:
            raise ConfigValidationError("Configuration parameter errors:\n  - " + "\n  - ".join(param_errors))
        enrichment = merged["DATA"].get("ENRICHMENT")
        if enrichment:
            params = enrichment.get("PARAMS", {})
            if "enrichment_start" in params:
                merged["DATA"]["TRANSFORM"]["PARAMS"]["enrichment_start"] = params["enrichment_start"]
        return merged
    return process_config(str(source))


def process_config(config_path: str) -> Dict[str, Any]:
    """Process configuration file through full validation pipeline.

    Pipeline stages:
    1. Validate file exists and is readable
    2. Parse and validate format (YAML/JSON)
    3. Merge with defaults (deep merge)
    4. Validate structure (required sections/fields)
    5. Validate parameters (dates, model-specific)

    Args:
        config_path: Path to configuration file.

    Returns:
        Fully validated and merged configuration dictionary.

    Raises:
        ConfigValidationError: If any validation stage fails.
    """
    # Stage 1: File validation
    validated_path = _validate_file(config_path)

    # Stage 2: Format validation (parse file)
    user_config = _validate_format(validated_path)

    # Load defaults
    defaults = get_defaults()

    # Stage 3: Merge with defaults
    merged_config = deep_merge(defaults, user_config)

    # Stage 4: Structure validation
    structure_errors = _validate_structure(merged_config)
    if structure_errors:
        raise ConfigValidationError("Configuration structure errors:\n  - " + "\n  - ".join(structure_errors))

    # Stage 5: Parameter validation
    param_errors = _validate_parameters(merged_config)
    if param_errors:
        raise ConfigValidationError("Configuration parameter errors:\n  - " + "\n  - ".join(param_errors))

    # Stage 6: Inject enrichment_start into TRANSFORM.PARAMS if ENRICHMENT is configured
    # This makes enrichment configuration explicit and predictable
    enrichment = merged_config["DATA"].get("ENRICHMENT")
    if enrichment:
        params = enrichment.get("PARAMS", {})
        if "enrichment_start" in params:
            merged_config["DATA"]["TRANSFORM"]["PARAMS"]["enrichment_start"] = params["enrichment_start"]

    return merged_config
