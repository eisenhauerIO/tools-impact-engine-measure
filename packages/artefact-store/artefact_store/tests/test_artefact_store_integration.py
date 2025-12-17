"""Integration tests for artefact store backends."""

import pytest
import tempfile
import json
from pathlib import Path
from artefact_store import create_artefact_store, FileArtefactStore, S3ArtefactStore

class TestArtefactStoreFactory:
    """Tests for artefact store factory functionality."""
    
    def test_create_file_store_from_path(self):
        """Test creating file artefact store from local path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = create_artefact_store(tmpdir)
            assert isinstance(store, FileArtefactStore)
            assert store.base_url == f"file://{tmpdir}"
    
    def test_create_file_store_from_file_url(self):
        """Test creating file artefact store from file:// URL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_url = f"file://{tmpdir}"
            store = create_artefact_store(file_url)
            assert isinstance(store, FileArtefactStore)
            assert store.base_url == file_url
    
    def test_create_s3_store_from_url(self):
        """Test creating S3 artefact store from s3:// URL."""
        store = create_artefact_store("s3://test-bucket/prefix")
        assert isinstance(store, S3ArtefactStore)
        assert store.bucket == "test-bucket"
        assert store.prefix == "prefix"
    
    def test_create_s3_store_without_prefix(self):
        """Test creating S3 artefact store without prefix."""
        store = create_artefact_store("s3://test-bucket")
        assert isinstance(store, S3ArtefactStore)
        assert store.bucket == "test-bucket"
        assert store.prefix == ""

class TestFileArtefactStore:
    """Tests for file artefact store backend."""
    
    def test_store_and_load_json(self):
        """Test storing and loading JSON data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = create_artefact_store(tmpdir)
            
            test_data = {"key": "value", "number": 42}
            stored_url = store.store_json("test.json", test_data)
            
            # Verify URL format
            assert stored_url.startswith("file://")
            assert "test.json" in stored_url
            
            # Load and verify data
            loaded_data = store.load_json("test.json")
            assert loaded_data == test_data
    
    def test_tenant_isolation(self):
        """Test that different tenants have isolated artefact storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = create_artefact_store(tmpdir)
            
            # Store data for tenant A
            data_a = {"tenant": "A", "value": 100}
            store.store_json("data.json", data_a, tenant_id="tenant_a")
            
            # Store data for tenant B
            data_b = {"tenant": "B", "value": 200}
            store.store_json("data.json", data_b, tenant_id="tenant_b")
            
            # Verify isolation
            loaded_a = store.load_json("data.json", tenant_id="tenant_a")
            loaded_b = store.load_json("data.json", tenant_id="tenant_b")
            
            assert loaded_a == data_a
            assert loaded_b == data_b
            assert loaded_a != loaded_b
    
    def test_default_tenant(self):
        """Test default tenant behavior."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = create_artefact_store(tmpdir)
            
            test_data = {"default": True}
            store.store_json("test.json", test_data)  # No tenant_id specified
            
            # Should be accessible with default tenant
            loaded_data = store.load_json("test.json", tenant_id="default")
            assert loaded_data == test_data
            
            # Should also be accessible without specifying tenant
            loaded_data_implicit = store.load_json("test.json")
            assert loaded_data_implicit == test_data
    
    def test_nested_paths(self):
        """Test storing artefacts in nested directory structures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = create_artefact_store(tmpdir)
            
            test_data = {"nested": True}
            stored_url = store.store_json("jobs/job_123/results.json", test_data, "tenant_x")
            
            # Verify file was created in correct nested structure
            assert "jobs/job_123/results.json" in stored_url
            
            # Verify data can be loaded
            loaded_data = store.load_json("jobs/job_123/results.json", "tenant_x")
            assert loaded_data == test_data

class TestS3ArtefactStore:
    """Tests for S3 artefact store backend (mocked)."""
    
    def test_store_and_load_json(self):
        """Test storing and loading JSON data in mocked S3."""
        store = create_artefact_store("s3://test-bucket/impact-engine")
        
        test_data = {"s3_test": True, "value": 42}
        stored_url = store.store_json("test.json", test_data)
        
        # Verify S3 URL format
        assert stored_url.startswith("s3://test-bucket/")
        assert "impact-engine" in stored_url
        assert "test.json" in stored_url
        
        # Load and verify data
        loaded_data = store.load_json("test.json")
        assert loaded_data == test_data
    
    def test_s3_tenant_isolation(self):
        """Test tenant isolation in S3 artefact store."""
        store = create_artefact_store("s3://test-bucket/prefix")
        
        # Store data for different tenants
        data_1 = {"tenant": "company_1"}
        data_2 = {"tenant": "company_2"}
        
        url_1 = store.store_json("config.json", data_1, "company_1")
        url_2 = store.store_json("config.json", data_2, "company_2")
        
        # URLs should be different
        assert url_1 != url_2
        assert "company_1" in url_1
        assert "company_2" in url_2
        
        # Data should be isolated
        loaded_1 = store.load_json("config.json", "company_1")
        loaded_2 = store.load_json("config.json", "company_2")
        
        assert loaded_1 == data_1
        assert loaded_2 == data_2
    
    def test_s3_mock_directory_structure(self):
        """Test that S3 mock creates expected directory structure."""
        store = create_artefact_store("s3://my-bucket/data")
        
        store.store_json("test.json", {"test": True}, "tenant_abc")
        
        # Verify mock directory exists
        mock_path = Path(".mock_s3/my-bucket/data/tenants/tenant_abc/test.json")
        assert mock_path.exists()
        
        # Verify content
        with open(mock_path, 'r') as f:
            content = json.load(f)
        assert content == {"test": True}

class TestURLParsing:
    """Tests for URL parsing functionality."""
    
    def test_parse_local_paths(self):
        """Test parsing various local path formats."""
        from artefact_store.url_parser import parse_storage_url
        
        # Relative path
        result = parse_storage_url("./data")
        assert result == {"scheme": "file", "path": "./data"}
        
        # Absolute path
        result = parse_storage_url("/tmp/data")
        assert result == {"scheme": "file", "path": "/tmp/data"}
        
        # File URL
        result = parse_storage_url("file:///app/data")
        assert result == {"scheme": "file", "path": "/app/data"}
    
    def test_parse_s3_urls(self):
        """Test parsing S3 URLs."""
        from artefact_store.url_parser import parse_storage_url
        
        # S3 with prefix
        result = parse_storage_url("s3://bucket/prefix/path")
        assert result == {"scheme": "s3", "bucket": "bucket", "prefix": "prefix/path"}
        
        # S3 without prefix
        result = parse_storage_url("s3://bucket")
        assert result == {"scheme": "s3", "bucket": "bucket", "prefix": ""}
    
    def test_normalize_file_urls(self):
        """Test file URL normalization."""
        from artefact_store.url_parser import normalize_to_file_url
        
        assert normalize_to_file_url("./data") == "file://./data"
        assert normalize_to_file_url("/tmp/data") == "file:///tmp/data"

class TestArtefactStoreIntegrationWithEngine:
    """Integration tests with the main engine."""
    
    def test_engine_with_file_store(self):
        """Test engine works with file artefact store URL."""
        # This would require mocking the full engine pipeline
        # For now, just test that artefact store creation works
        store = create_artefact_store("./test_data")
        assert isinstance(store, FileArtefactStore)
    
    def test_engine_with_s3_store(self):
        """Test engine works with S3 artefact store URL."""
        # This would require mocking the full engine pipeline
        # For now, just test that artefact store creation works
        store = create_artefact_store("s3://test-bucket/impact-engine")
        assert isinstance(store, S3ArtefactStore)

class TestErrorHandling:
    """Tests for error handling in artefact store operations."""
    
    def test_unsupported_scheme(self):
        """Test error handling for unsupported URL schemes."""
        with pytest.raises(ValueError, match="Unsupported scheme"):
            create_artefact_store("ftp://example.com/data")
    
    def test_file_not_found(self):
        """Test error handling when loading non-existent artefacts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = create_artefact_store(tmpdir)
            
            with pytest.raises(FileNotFoundError):
                store.load_json("nonexistent.json")
    
    def test_invalid_json(self):
        """Test error handling for invalid JSON data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = create_artefact_store(tmpdir)
            
            # Create invalid JSON file manually
            invalid_file = Path(tmpdir) / "tenants/default/invalid.json"
            invalid_file.parent.mkdir(parents=True, exist_ok=True)
            invalid_file.write_text("invalid json content")
            
            with pytest.raises(json.JSONDecodeError):
                store.load_json("invalid.json")