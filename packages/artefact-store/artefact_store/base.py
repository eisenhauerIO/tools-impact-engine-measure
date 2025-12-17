"""Base artefact store interface for Impact Engine."""

from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd

class ArtefactStoreInterface(ABC):
    """Abstract artefact store interface for multi-tenant persistence."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    @abstractmethod
    def store_json(self, path: str, data: Dict[str, Any], tenant_id: str = "default") -> str:
        """Store JSON data and return the storage URL."""
        pass
    
    @abstractmethod
    def load_json(self, path: str, tenant_id: str = "default") -> Dict[str, Any]:
        """Load JSON data from storage."""
        pass
    
    def _build_tenant_path(self, path: str, tenant_id: str) -> str:
        """Build tenant-isolated path."""
        return f"tenants/{tenant_id}/{path}"