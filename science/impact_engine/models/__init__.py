"""Models layer for the impact_engine package."""

from .base import ModelInterface, ModelResult
from .factory import (
    MODEL_REGISTRY,
    create_models_manager,
    create_models_manager_from_config,
)
from .manager import FitOutput, ModelsManager

__all__ = [
    "FitOutput",
    "ModelInterface",
    "ModelResult",
    "ModelsManager",
    "MODEL_REGISTRY",
    "create_models_manager",
    "create_models_manager_from_config",
]
