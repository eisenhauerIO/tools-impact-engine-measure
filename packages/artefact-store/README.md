# Impact Engine Artefact Store

Artefact store for multi-tenant persistence of analysis results and data products supporting file and S3 backends.

## Features

- Multi-tenant isolation
- File and S3 storage backends
- URL-based configuration
- JSON data serialization

## Usage

```python
from artefact_store import create_artefact_store

# File artefact store
store = create_artefact_store("./data")

# S3 artefact store
store = create_artefact_store("s3://my-bucket/prefix")

# Store analysis results
url = store.store_json("results.json", {"key": "value"}, tenant_id="tenant1")

# Load analysis results
data = store.load_json("results.json", tenant_id="tenant1")
```

## Installation

```bash
pip install artefact-store
```

For development:
```bash
pip install -e .
```

## Development

```bash
# Run tests
hatch run test

# Format code
hatch run format

# Lint code
hatch run lint

# Build package
hatch build
```