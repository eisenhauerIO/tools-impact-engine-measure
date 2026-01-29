"""Storage layer for the impact_engine package."""

from .base import StorageInterface
from .factory import (
    STORAGE_REGISTRY,
    create_storage_manager,
    create_storage_manager_from_config,
)
from .manager import StorageManager

__all__ = [
    "StorageInterface",
    "StorageManager",
    "STORAGE_REGISTRY",
    "create_storage_manager",
    "create_storage_manager_from_config",
]
