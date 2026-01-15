"""Core integration modules for impact-engine."""

from .config_bridge import ConfigBridge
from .contracts import MetricsSchema, ProductSchema, Schema, TransformSchema
from .validation import ConfigValidationError, deep_merge, get_defaults, process_config

__all__ = [
    "ConfigBridge",
    "ConfigValidationError",
    "MetricsSchema",
    "ProductSchema",
    "Schema",
    "TransformSchema",
    "deep_merge",
    "get_defaults",
    "process_config",
]
