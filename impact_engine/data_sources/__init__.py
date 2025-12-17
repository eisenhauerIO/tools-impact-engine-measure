"""
Data Abstraction Layer - Unified interface for business metrics retrieval.
"""

from .base import DataSourceInterface, DataNotFoundError, TimeRange
from .manager import DataSourceManager
from .simulator import SimulatorDataSource

__all__ = [
    "DataSourceInterface",
    "DataNotFoundError", 
    "TimeRange",
    "DataSourceManager",
    "SimulatorDataSource",
]