"""S3 artefact store backend (mocked for development)."""

import json
from pathlib import Path
from typing import Dict, Any
from .base import ArtefactStoreInterface
from .url_parser import parse_storage_url

class S3ArtefactStore(ArtefactStoreInterface):
    """S3 artefact store backend that mocks S3 operations locally."""
    
    def __init__(self, base_url: str):
        super().__init__(base_url)
        parsed = parse_storage_url(base_url)
        self.bucket = parsed["bucket"]
        self.prefix = parsed["prefix"]
        
        # Mock S3 with local directory
        self.mock_path = Path(f".mock_s3/{self.bucket}")
        self.mock_path.mkdir(parents=True, exist_ok=True)
    
    def store_json(self, path: str, data: Dict[str, Any], tenant_id: str = "default") -> str:
        """Store JSON data to mocked S3 location."""
        tenant_path = self._build_tenant_path(path, tenant_id)
        full_path = self.mock_path / self.prefix / tenant_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        s3_path = f"{self.prefix}/{tenant_path}" if self.prefix else tenant_path
        return f"s3://{self.bucket}/{s3_path}"
    
    def load_json(self, path: str, tenant_id: str = "default") -> Dict[str, Any]:
        """Load JSON data from mocked S3 location."""
        tenant_path = self._build_tenant_path(path, tenant_id)
        full_path = self.mock_path / self.prefix / tenant_path
        
        with open(full_path, 'r') as f:
            return json.load(f)