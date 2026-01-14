"""
Pluggable Configuration Validators.

This module provides a framework for validating configuration sections
with pluggable validators. Each validator handles a specific section
of the configuration, making it easy to extend validation for new
sections or model types.

Usage:
    # Register a custom validator
    @register_validator("custom_section")
    class CustomValidator(ConfigValidator):
        def validate(self, config: Dict) -> List[ConfigError]:
            errors = []
            if "required_field" not in config:
                errors.append(ConfigError("required_field", "Field is required"))
            return errors

    # Validate configuration
    errors = validate_config(config)
    if errors:
        raise ConfigurationError(errors)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type


@dataclass
class ConfigError:
    """Represents a single configuration validation error."""

    field: str
    message: str
    section: Optional[str] = None

    def __str__(self) -> str:
        if self.section:
            return f"{self.section}.{self.field}: {self.message}"
        return f"{self.field}: {self.message}"


class ConfigValidator(ABC):
    """Abstract base class for configuration validators.

    Validators are responsible for validating a specific section of the
    configuration. They return a list of errors (empty if valid).
    """

    @abstractmethod
    def validate(self, config: Dict[str, Any]) -> List[ConfigError]:
        """Validate the configuration section.

        Args:
            config: The configuration section to validate.

        Returns:
            List of ConfigError objects. Empty list means valid.
        """
        pass


# Registry of validators by section name
_VALIDATOR_REGISTRY: Dict[str, Type[ConfigValidator]] = {}


def register_validator(section: str) -> Callable[[Type[ConfigValidator]], Type[ConfigValidator]]:
    """Decorator to register a validator for a configuration section.

    Args:
        section: The section name this validator handles (e.g., "DATA.SOURCE").

    Returns:
        Decorator function.
    """

    def decorator(cls: Type[ConfigValidator]) -> Type[ConfigValidator]:
        _VALIDATOR_REGISTRY[section] = cls
        return cls

    return decorator


def get_validator(section: str) -> Optional[ConfigValidator]:
    """Get an instance of the validator for the given section.

    Args:
        section: The section name.

    Returns:
        Validator instance, or None if no validator registered.
    """
    validator_cls = _VALIDATOR_REGISTRY.get(section)
    if validator_cls:
        return validator_cls()
    return None


def list_validators() -> List[str]:
    """List all registered validator sections."""
    return list(_VALIDATOR_REGISTRY.keys())


# ---------------------------------------------------------------------------
# Built-in Validators
# ---------------------------------------------------------------------------


@register_validator("DATA.SOURCE")
class DataSourceValidator(ConfigValidator):
    """Validates DATA.SOURCE configuration section."""

    def validate(self, config: Dict[str, Any]) -> List[ConfigError]:
        errors: List[ConfigError] = []
        section = "DATA.SOURCE"

        # Check required fields
        if "TYPE" not in config:
            errors.append(ConfigError("TYPE", "Required field missing", section))

        if "CONFIG" not in config:
            errors.append(ConfigError("CONFIG", "Required field missing", section))
            return errors  # Can't validate CONFIG if missing

        source_config = config["CONFIG"]

        # Validate CONFIG fields
        for field in ["PATH", "START_DATE", "END_DATE"]:
            if field not in source_config:
                errors.append(ConfigError(field, "Required field missing", f"{section}.CONFIG"))

        # Validate date formats if present
        if "START_DATE" in source_config:
            error = self._validate_date(source_config["START_DATE"], "START_DATE", f"{section}.CONFIG")
            if error:
                errors.append(error)

        if "END_DATE" in source_config:
            error = self._validate_date(source_config["END_DATE"], "END_DATE", f"{section}.CONFIG")
            if error:
                errors.append(error)

        # Validate date consistency
        if "START_DATE" in source_config and "END_DATE" in source_config:
            try:
                start = datetime.strptime(source_config["START_DATE"], "%Y-%m-%d")
                end = datetime.strptime(source_config["END_DATE"], "%Y-%m-%d")
                if start > end:
                    errors.append(
                        ConfigError(
                            "START_DATE",
                            f"Must be before or equal to END_DATE ({source_config['END_DATE']})",
                            f"{section}.CONFIG",
                        )
                    )
            except ValueError:
                pass  # Date format errors already captured above

        return errors

    def _validate_date(self, value: str, field: str, section: str) -> Optional[ConfigError]:
        """Validate date format."""
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return None
        except ValueError:
            return ConfigError(field, "Invalid date format. Expected YYYY-MM-DD", section)


@register_validator("DATA.TRANSFORM")
class TransformValidator(ConfigValidator):
    """Validates DATA.TRANSFORM configuration section."""

    def validate(self, config: Dict[str, Any]) -> List[ConfigError]:
        errors: List[ConfigError] = []
        section = "DATA.TRANSFORM"

        if "FUNCTION" not in config:
            errors.append(ConfigError("FUNCTION", "Required field missing", section))

        return errors


@register_validator("MEASUREMENT")
class MeasurementValidator(ConfigValidator):
    """Validates MEASUREMENT configuration section.

    This validator supports model-specific validation by delegating to
    registered model validators.
    """

    def validate(self, config: Dict[str, Any]) -> List[ConfigError]:
        errors: List[ConfigError] = []
        section = "MEASUREMENT"

        if "MODEL" not in config:
            errors.append(ConfigError("MODEL", "Required field missing", section))
            return errors

        if "PARAMS" not in config:
            errors.append(ConfigError("PARAMS", "Required field missing", section))
            return errors

        # Delegate to model-specific validator if registered
        model_type = config["MODEL"]
        model_validator = get_validator(f"MEASUREMENT.{model_type}")
        if model_validator:
            model_errors = model_validator.validate(config["PARAMS"])
            errors.extend(model_errors)

        return errors


@register_validator("MEASUREMENT.interrupted_time_series")
class ITSParamsValidator(ConfigValidator):
    """Validates interrupted_time_series model parameters."""

    def validate(self, config: Dict[str, Any]) -> List[ConfigError]:
        errors: List[ConfigError] = []
        section = "MEASUREMENT.PARAMS"

        if "intervention_date" not in config:
            errors.append(
                ConfigError("intervention_date", "Required for interrupted_time_series model", section)
            )
        else:
            # Validate date format
            try:
                datetime.strptime(config["intervention_date"], "%Y-%m-%d")
            except ValueError:
                errors.append(
                    ConfigError("intervention_date", "Invalid date format. Expected YYYY-MM-DD", section)
                )

        return errors


@register_validator("MEASUREMENT.metrics_approximation")
class MetricsApproximationParamsValidator(ConfigValidator):
    """Validates metrics_approximation model parameters.

    Metrics approximation has no required parameters - all are optional.
    """

    def validate(self, config: Dict[str, Any]) -> List[ConfigError]:
        # All params are optional for metrics_approximation
        return []


# ---------------------------------------------------------------------------
# Main Validation Function
# ---------------------------------------------------------------------------


def validate_config_with_validators(config: Dict[str, Any]) -> List[ConfigError]:
    """Validate configuration using registered validators.

    This function validates all sections of the configuration by
    delegating to registered validators.

    Args:
        config: Full configuration dictionary.

    Returns:
        List of all validation errors. Empty if valid.
    """
    all_errors: List[ConfigError] = []

    # Validate DATA section
    if "DATA" not in config:
        all_errors.append(ConfigError("DATA", "Required section missing"))
    else:
        data = config["DATA"]

        # Validate DATA.SOURCE
        if "SOURCE" not in data:
            all_errors.append(ConfigError("SOURCE", "Required field missing", "DATA"))
        else:
            validator = get_validator("DATA.SOURCE")
            if validator:
                all_errors.extend(validator.validate(data["SOURCE"]))

        # Validate DATA.TRANSFORM if present
        if "TRANSFORM" in data:
            validator = get_validator("DATA.TRANSFORM")
            if validator:
                all_errors.extend(validator.validate(data["TRANSFORM"]))

    # Validate MEASUREMENT section
    if "MEASUREMENT" not in config:
        all_errors.append(ConfigError("MEASUREMENT", "Required section missing"))
    else:
        validator = get_validator("MEASUREMENT")
        if validator:
            all_errors.extend(validator.validate(config["MEASUREMENT"]))

    return all_errors
