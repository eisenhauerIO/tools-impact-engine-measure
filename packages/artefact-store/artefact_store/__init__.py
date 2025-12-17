"""Artefact store for Impact Engine analysis results and data products."""

from .factory import create_artefact_store
from .base import ArtefactStoreInterface
from .file import FileArtefactStore
from .s3 import S3ArtefactStore

__all__ = ['create_artefact_store', 'ArtefactStoreInterface', 'FileArtefactStore', 'S3ArtefactStore']
__version__ = "0.1.0"