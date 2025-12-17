"""Artefact store factory for creating artefact store backends."""

from .url_parser import parse_storage_url, normalize_to_file_url
from .file import FileArtefactStore
from .s3 import S3ArtefactStore

def create_artefact_store(storage_url: str):
    """Create artefact store backend from URL or path."""
    # Convert local paths to file:// URLs
    if "://" not in storage_url:
        storage_url = normalize_to_file_url(storage_url)
    
    parsed = parse_storage_url(storage_url)
    
    if parsed["scheme"] == "file":
        return FileArtefactStore(storage_url)
    elif parsed["scheme"] == "s3":
        return S3ArtefactStore(storage_url)
    else:
        raise ValueError(f"Unsupported scheme: {parsed['scheme']}")