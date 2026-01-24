"""Core integration modules for impact-engine."""

from .config_bridge import ConfigBridge
from .contracts import ColumnContract, MetricsSchema, ProductSchema, Schema, TransformSchema
from .registry import Registry
from .transforms import (
    TRANSFORM_REGISTRY,
    apply_transform,
    get_transform,
    register_transform,
)
from .validation import ConfigValidationError, deep_merge, get_defaults, process_config

__all__ = [
    "ColumnContract",
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
    "process_config",
    "register_transform",
]
