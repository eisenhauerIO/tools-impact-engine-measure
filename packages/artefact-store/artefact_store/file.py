"""File artefact store backend for local filesystem."""

import json
from pathlib import Path
from typing import Dict, Any
from .base import ArtefactStoreInterface

class FileArtefactStore(ArtefactStoreInterface):
    """Local filesystem artefact store implementation with tenant isolation."""
    
    def __init__(self, base_url: str):
        super().__init__(base_url)
        # Extract path from file://path
        self.base_path = Path(base_url.replace("file://", ""))
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def store_json(self, path: str, data: Dict[str, Any], tenant_id: str = "default") -> str:
        """Store JSON data to local file with tenant isolation."""
        full_path = self.base_path / self._build_tenant_path(path, tenant_id)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        return f"file://{full_path}"
    
    def load_json(self, path: str, tenant_id: str = "default") -> Dict[str, Any]:
        """Load JSON data from local file with tenant isolation."""
        full_path = self.base_path / self._build_tenant_path(path, tenant_id)
        
        with open(full_path, 'r') as f:
            return json.load(f)