"""URL parsing utilities for artefact store backends."""

def parse_storage_url(input_path: str) -> dict:
    """
    Parse storage URL into components.
    
    Examples:
        "./data" → {"scheme": "file", "path": "./data"}
        "s3://bucket/prefix" → {"scheme": "s3", "bucket": "bucket", "prefix": "prefix"}
    """
    if "://" in input_path:
        scheme, rest = input_path.split("://", 1)
        if scheme == "s3":
            parts = rest.split("/", 1)
            return {
                "scheme": "s3", 
                "bucket": parts[0], 
                "prefix": parts[1] if len(parts) > 1 else ""
            }
        return {"scheme": scheme, "path": rest}
    else:
        return {"scheme": "file", "path": input_path}

def normalize_to_file_url(path: str) -> str:
    """Convert local path to file:// URL."""
    return f"file://{path}"