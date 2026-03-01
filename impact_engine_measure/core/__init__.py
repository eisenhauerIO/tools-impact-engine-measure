"""Core integration modules for impact-engine."""

from .config_bridge import ConfigBridge
from .contracts import MetricsSchema, ProductSchema, Schema, TransformSchema
from .registry import Registry
from .transforms import (
    TRANSFORM_REGISTRY,
    apply_transform,
    get_transform,
    register_transform,
)
from .validation import ConfigValidationError, deep_merge, get_defaults, load_config, process_config

__all__ = [
    "ConfigBridge",
    "ConfigValidationError",
    "MetricsSchema",
    "ProductSchema",
    "Registry",
    "Schema",
    "TRANSFORM_REGISTRY",
    "TransformSchema",
    "apply_transform",
    "deep_merge",
    "get_defaults",
    "get_transform",
    "load_config",
    "process_config",
    "register_transform",
]
