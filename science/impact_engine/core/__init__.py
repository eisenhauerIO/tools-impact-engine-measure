"""Core integration modules for impact-engine."""

from .config_bridge import ConfigBridge
from .contracts import MetricsSchema, ProductSchema, Schema, TransformSchema
from .transforms import (
    TRANSFORM_REGISTRY,
    apply_transform,
    get_transform,
    register_transform,
)
from .validation import ConfigValidationError, deep_merge, get_defaults, process_config

__all__ = [
    "ConfigBridge",
    "ConfigValidationError",
    "MetricsSchema",
    "ProductSchema",
    "Schema",
    "TRANSFORM_REGISTRY",
    "TransformSchema",
    "apply_transform",
    "deep_merge",
    "get_defaults",
    "get_transform",
    "process_config",
    "register_transform",
]
