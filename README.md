# Impact Engine Monorepo

A comprehensive package for evaluating causal impact of product interventions using business metrics and statistical modeling.

## Monorepo Structure

This repository is organized as a monorepo with the following packages:

- **`impact_engine/`** - Main impact analysis engine
- **`packages/artefact-store/`** - Independent artefact store for analysis results

## Overview

Impact Engine provides a unified framework for:
- **Metrics Collection**: Retrieve business metrics from various data sources (simulators, databases, APIs)
- **Statistical Modeling**: Apply causal inference models to measure intervention impact
- **Extensible Architecture**: Plugin-based system for custom metrics providers and models

## Quick Start

### Installation

For development (installs both packages in editable mode):
```bash
hatch run install-dev
```

For production:
```bash
pip install impact-engine
pip install artefact-store
```

### Basic Usage

```python
from impact_engine import evaluate_impact
from artefact_store import create_artefact_store
import pandas as pd

# Define products to analyze
products = pd.DataFrame({
    'product_id': ['prod1', 'prod2'],
    'name': ['Product 1', 'Product 2']
})

# Run impact analysis with storage
result_path = evaluate_impact(
    config_path='config.json',
    products=products,
    storage_url='./results',  # or 's3://bucket/prefix'
    tenant_id='my_company'
)

print(f"Results saved to: {result_path}")
```

### Configuration

Create a configuration file (`config.json`):

```json
{
  "DATA": {
    "TYPE": "simulator",
    "MODE": "rule",
    "SEED": 42,
    "START_DATE": "2024-01-01",
    "END_DATE": "2024-01-31"
  },
  "MEASUREMENT": {
    "MODEL": "interrupted_time_series",
    "PARAMS": {
      "INTERVENTION_DATE": "2024-01-15",
      "DEPENDENT_VARIABLE": "revenue",
      "order": [1, 0, 0],
      "seasonal_order": [0, 0, 0, 0]
    }
  }
}
```

## Architecture

Impact Engine follows a layered architecture with clear separation of concerns:

```
┌─────────────────┐
│   engine.py     │  ← Main orchestration layer
│ (evaluate_impact)│
└─────────────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌─────────┐ ┌─────────┐
│ Metrics │ │ Models  │  ← Specialized layers
│ Layer   │ │ Layer   │
└─────────┘ └─────────┘
    │         │
    ▼         ▼
┌─────────┐ ┌─────────┐
│Adapters │ │Adapters │  ← External integrations
└─────────┘ └─────────┘
```

### Core Components

- **`engine.py`**: Main orchestration engine that coordinates metrics and models
- **Metrics Layer**: Handles business metrics retrieval from various sources
- **Models Layer**: Applies statistical models for causal impact analysis

## Package Structure

```
impact_engine/
├── engine.py                    # Main orchestration engine
├── config.py                    # Configuration parsing
├── metrics/                     # Metrics collection layer
│   ├── base.py                 # MetricsInterface
│   ├── manager.py              # MetricsManager
│   └── adapter_catalog_simulator.py  # Built-in simulator
├── models/                      # Statistical modeling layer
│   ├── base.py                 # Model interface
│   ├── manager.py              # ModelsManager
│   └── adapter_interrupted_time_series.py  # Built-in ITS model
└── tests/                       # Comprehensive test suite
    ├── test_metrics_manager.py
    ├── test_metrics_catalog_simulator.py
    ├── test_models_manager.py
    ├── test_models_interrupted_time_series.py
    └── test_evaluate_impact.py
```

## Features

### Metrics Layer
- **Plugin Architecture**: Register custom metrics providers at runtime
- **Transformation Methods**: Explicit data format conversion between systems
- **Built-in Adapters**: Catalog simulator for testing and development
- **Standardized Schema**: Consistent data format across all providers

### Models Layer
- **Statistical Models**: Interrupted Time Series (ITS) with SARIMAX
- **Extensible Interface**: Add custom causal inference models
- **Connection Management**: Proper initialization and validation
- **Standardized Output**: Consistent results format across all models

### Configuration-Driven
- **Declarative Setup**: No code changes to switch providers or models
- **Environment Support**: Different configs for dev/staging/prod
- **Parameter Validation**: Early error detection with clear messages

## Advanced Usage

### Custom Metrics Provider

```python
from impact_engine.metrics import MetricsInterface, MetricsManager

class CustomMetricsAdapter(MetricsInterface):
    def connect(self, config):
        # Initialize connection
        return True
    
    def transform_outbound(self, products, start_date, end_date):
        # Transform to external format
        return formatted_params
    
    def transform_inbound(self, external_data):
        # Transform to standard format
        return standardized_df
    
    # ... implement other required methods

# Register and use
manager = MetricsManager(config)
manager.register_metrics("custom", CustomMetricsAdapter)
```

### Custom Model

```python
from impact_engine.models import Model, ModelsManager

class CustomModel(Model):
    def connect(self, config):
        # Initialize model
        return True
    
    def transform_outbound(self, data, intervention_date, **kwargs):
        # Transform to model format
        return model_params
    
    def transform_inbound(self, model_results):
        # Transform to standard format
        return standardized_results
    
    # ... implement other required methods

# Register and use
manager = ModelsManager(config)
manager.register_model("custom", CustomModel)
```

## Artefact Store Package

The artefact store layer has been extracted as an independent package (`packages/artefact-store/`) that provides:

- **Multi-tenant isolation**: Separate data by tenant/organization
- **Multiple backends**: File system and S3 (with local mock)
- **URL-based configuration**: `./data`, `s3://bucket/prefix`
- **JSON serialization**: Automatic handling of complex data types

### Artefact Store Usage

```python
from artefact_store import create_artefact_store

# File artefact store
store = create_artefact_store("./data")

# S3 artefact store  
store = create_artefact_store("s3://my-bucket/impact-engine")

# Store analysis results with tenant isolation
url = store.store_json("results.json", {"key": "value"}, tenant_id="company_a")

# Load analysis results
data = store.load_json("results.json", tenant_id="company_a")
```

## Development Commands

```bash
# Install packages in development mode
pip install -e packages/artefact-store
pip install -e .

# Run all tests (main + artefact store)
hatch run test-all

# Test main package only
hatch run test

# Format code
hatch run format
```

## Testing

Run the comprehensive test suite:

```bash
# All tests (main + artefact store packages)
hatch run test-all

# Main package tests only
pytest impact_engine/tests/

# Artefact store package tests only  
pytest packages/artefact-store/artefact_store/tests/
```

## Documentation

- [Metrics Layer Architecture](docs/data-abstraction-layer.md)
- [Models Layer Architecture](docs/modeling-abstraction-layer.md)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
