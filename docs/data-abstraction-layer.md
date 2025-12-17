# Metrics Layer Architecture

## Design Philosophy

The metrics layer follows a **plugin-based architecture** with three core principles:

### 1. **Uniform Interface**
All metrics providers implement the same `MetricsInterface`, ensuring consistent behavior regardless of the underlying data provider. Whether retrieving from a simulator, database, or API, the interface remains identical.

### 2. **Runtime Extensibility**
New metrics providers can be registered at runtime without modifying core code. This enables:
- External packages to provide metrics implementations
- Company-specific integrations without forking the codebase
- Easy testing with mock metrics providers

### 3. **Configuration-Driven Selection**
Metrics providers are selected via configuration, not code changes. The same analysis can run against different metrics sources by simply changing the config file.

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  engine.py      │───▶│ MetricsManager   │───▶│ MetricsInterface │
│ (evaluate_impact)│    └──────────────────┘    └─────────────────┘
└─────────────────┘             │                         ▲
                                ▼                         │
                       ┌──────────────────┐              │
                       │ Configuration    │              │
                       │ Parser           │              │
                       └──────────────────┘              │
                                                         │
                    ┌─────────────────┬─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼                 ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │ Catalog      │  │ Database     │  │ API          │  │ Custom       │
            │ Simulator    │  │ Adapter      │  │ Adapter      │  │ Adapter      │
            └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

## Package Structure

```
impact_engine/
├── engine.py                    # Main orchestration engine
├── metrics/
│   ├── __init__.py             # Public API exports
│   ├── base.py                 # MetricsInterface + common utilities
│   ├── manager.py              # MetricsManager coordination logic
│   └── adapter_catalog_simulator.py  # Built-in simulator implementation
└── models/
    ├── __init__.py             # Public API exports
    ├── base.py                 # Model interface + common utilities
    ├── manager.py              # ModelsManager coordination logic
    └── adapter_interrupted_time_series.py  # Built-in ITS model
```

**Design Rationale**: Each file has a single responsibility, making the codebase easier to navigate, test, and extend.

## Registration API

### Direct Registration
```python
from impact_engine.metrics import MetricsManager

manager = MetricsManager(config)
manager.register_metrics("salesforce", SalesforceMetricsAdapter)
```

**Why Direct Registration**: Simplest approach that covers 90% of use cases. No complex setup, no packaging requirements, immediate availability.

## Transformation Architecture

All metrics adapters implement explicit transformation methods:

### Outbound Transformation
Converts impact engine format to external system format:
```python
def transform_outbound(self, products: pd.DataFrame, start_date: str, end_date: str) -> Dict[str, Any]:
    """Transform impact engine format to external system format"""
    # Handle field mapping, data types, naming conventions
    # Apply any required filtering or preprocessing
    return formatted_parameters
```

### Inbound Transformation  
Converts external system response to impact engine format:
```python
def transform_inbound(self, external_data: Any) -> pd.DataFrame:
    """Transform external system response to impact engine format"""
    # Normalize field names, data types, structures
    # Handle missing data, validation, cleanup
    return standardized_dataframe
```

## Standardized Schema

All metrics adapters return the same schema:
```python
{
    'product_id': str,
    'name': str, 
    'category': str,
    'price': float,
    'date': datetime,
    'sales_volume': int,        # Standardized from source-specific fields
    'revenue': float,
    'inventory_level': int,     # Calculated if not available
    'customer_engagement': float,
    'metrics_source': str,      # Source identifier
    'retrieval_timestamp': datetime
}
```

**Design Rationale**: Consistent schema enables analysis code to work across any metrics source. Source-specific transformations happen within each adapter's transformation methods.

## Configuration Philosophy

Metrics sources are configured declaratively:
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
      "DEPENDENT_VARIABLE": "revenue"
    }
  }
}
```

**Benefits**:
- Same analysis code works with different metrics sources
- Environment-specific configurations (dev/staging/prod)
- No code changes required to switch metrics sources

## Extension Points

### For Metrics Adapter Authors
1. Implement `MetricsInterface`
2. Implement `connect()` and `validate_connection()` methods
3. Implement `transform_outbound()` and `transform_inbound()` methods
4. Handle source-specific connection logic
5. Register with `MetricsManager`

### For Application Developers
1. Create configuration file
2. Register custom metrics adapters (if needed)
3. Call `evaluate_impact()` from `engine.py` or use `MetricsManager` directly

## Error Handling Strategy

- **Connection Errors**: Fail fast with clear error messages
- **Data Not Found**: Return empty DataFrame with correct schema
- **Invalid Configuration**: Validate early, provide specific guidance
- **Transformation Errors**: Log warnings, continue with available data

This approach ensures robust operation while providing clear feedback for troubleshooting.