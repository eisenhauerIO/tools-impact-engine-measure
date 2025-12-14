# Data Sources Architecture

## Design Philosophy

The data abstraction layer follows a **plugin-based architecture** with three core principles:

### 1. **Uniform Interface**
All data sources implement the same `DataSourceInterface`, ensuring consistent behavior regardless of the underlying data provider. Whether retrieving from a simulator, database, or API, the interface remains identical.

### 2. **Runtime Extensibility**
New data sources can be registered at runtime without modifying core code. This enables:
- External packages to provide data source implementations
- Company-specific integrations without forking the codebase
- Easy testing with mock data sources

### 3. **Configuration-Driven Selection**
Data sources are selected via configuration, not code changes. The same analysis can run against different data sources by simply changing the config file.

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  evaluate_impact │───▶│ DataSourceManager │───▶│ DataSourceInterface │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                         ▲
                                ▼                         │
                       ┌──────────────────┐              │
                       │ Configuration    │              │
                       │ Parser           │              │
                       └──────────────────┘              │
                                                         │
                    ┌─────────────────┬─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼                 ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │ Simulator    │  │ Database     │  │ API          │  │ Custom       │
            │ DataSource   │  │ DataSource   │  │ DataSource   │  │ DataSource   │
            └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

## Package Structure

```
impact_engine/data_sources/
├── __init__.py          # Public API exports
├── base.py             # DataSourceInterface + common utilities
├── manager.py          # DataSourceManager coordination logic
└── simulator.py        # Built-in simulator implementation
```

**Design Rationale**: Each file has a single responsibility, making the codebase easier to navigate, test, and extend.

## Registration API

### Direct Registration
```python
from impact_engine.data_sources import DataSourceManager

manager = DataSourceManager()
manager.register_data_source("salesforce", SalesforceDataSource)
```

**Why Direct Registration**: Simplest approach that covers 90% of use cases. No complex setup, no packaging requirements, immediate availability.

## Standardized Schema

All data sources return the same schema:
```python
{
    'product_id': str,
    'name': str, 
    'category': str,
    'price': float,
    'date': datetime,
    'sales_volume': int,        # Standardized from source-specific fields
    'revenue': float,
    'inventory_level': int,     # Simulated if not available
    'customer_engagement': float,
    'data_source': str,         # Source identifier
    'retrieval_timestamp': datetime
}
```

**Design Rationale**: Consistent schema enables analysis code to work across any data source. Source-specific transformations happen within each data source implementation.

## Configuration Philosophy

Data sources are configured declaratively:
```json
{
  "data_source": {
    "type": "salesforce",
    "connection": { "instance_url": "...", "token": "..." }
  },
  "time_range": { "start_date": "2024-11-01", "end_date": "2024-11-30" }
}
```

**Benefits**:
- Same analysis code works with different data sources
- Environment-specific configurations (dev/staging/prod)
- No code changes required to switch data sources

## Extension Points

### For Data Source Authors
1. Implement `DataSourceInterface`
2. Handle source-specific connection logic
3. Transform to standardized schema
4. Register with `DataSourceManager`

### For Application Developers
1. Create configuration file
2. Register custom data sources (if needed)
3. Call `evaluate_impact()` or use `DataSourceManager` directly

## Error Handling Strategy

- **Connection Errors**: Fail fast with clear error messages
- **Data Not Found**: Return empty DataFrame with correct schema
- **Invalid Configuration**: Validate early, provide specific guidance
- **Transformation Errors**: Log warnings, continue with available data

This approach ensures robust operation while providing clear feedback for troubleshooting.