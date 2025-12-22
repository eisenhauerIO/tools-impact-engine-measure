"""Core integration modules for impact-engine."""

from .config_bridge import ConfigBridge
from .contracts import MetricsSchema, ProductSchema, Schema

__all__ = ["ConfigBridge", "MetricsSchema", "ProductSchema", "Schema"]
