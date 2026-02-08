"""
Factory functions for creating ModelsManager instances.

This module handles model selection based on configuration,
keeping the ModelsManager class simple and focused on coordination.
"""

from typing import Any, Dict

from ..config import parse_config_file
from ..core import Registry
from .base import ModelInterface
from .manager import ModelsManager

# Registry of available models - adapters self-register via decorator
MODEL_REGISTRY: Registry[ModelInterface] = Registry(ModelInterface, "model")


def create_models_manager(config_path: str) -> ModelsManager:
    """Create a ModelsManager from a configuration file.

    This factory function:
    1. Parses the configuration file
    2. Selects the appropriate model based on MEASUREMENT.MODEL
    3. Creates and returns a configured ModelsManager

    Args:
        config_path: Path to the configuration file (YAML or JSON).

    Returns:
        ModelsManager: Configured manager with the appropriate model.

    Raises:
        ValueError: If the configured model type is not supported.
        FileNotFoundError: If the configuration file doesn't exist.
    """
    config = parse_config_file(config_path)
    measurement_config = config["MEASUREMENT"]

    return create_models_manager_from_config(measurement_config)


def create_models_manager_from_config(
    measurement_config: Dict[str, Any],
) -> ModelsManager:
    """Create a ModelsManager from a MEASUREMENT configuration dict.

    Args:
        measurement_config: The MEASUREMENT configuration block.

    Returns:
        ModelsManager: Configured manager with the appropriate model.

    Raises:
        ValueError: If the configured model type is not supported.
    """
    model_type = measurement_config.get("MODEL", "interrupted_time_series")

    model = get_model_adapter(model_type)

    return ModelsManager(
        measurement_config=measurement_config,
        model=model,
    )


def get_model_adapter(model_type: str) -> ModelInterface:
    """Get an instance of the model adapter for the given type.

    Args:
        model_type: The type of model (e.g., "interrupted_time_series").

    Returns:
        ModelInterface: An instance of the appropriate model.

    Raises:
        ValueError: If the model type is not supported.
    """
    return MODEL_REGISTRY.get(model_type)


# Import adapters to trigger self-registration via decorators
# These imports must be at the end after MODEL_REGISTRY is defined
from .experiment import ExperimentAdapter  # noqa: E402, F401
from .interrupted_time_series import InterruptedTimeSeriesAdapter  # noqa: E402, F401
from .metrics_approximation import MetricsApproximationAdapter  # noqa: E402, F401
from .nearest_neighbour_matching import NearestNeighbourMatchingAdapter  # noqa: E402, F401
from .subclassification import SubclassificationAdapter  # noqa: E402, F401
from .synthetic_control import SyntheticControlAdapter  # noqa: E402, F401
