# Modeling Abstraction Layer

## Design Philosophy

The modeling abstraction layer follows a **unified interface architecture** with three core principles:

### 1. **Consistent Model Interface**
All models implement the same `ModelInterface`, ensuring uniform behavior regardless of the underlying statistical approach. Whether using interrupted time series, causal inference, or regression discontinuity, the interface remains identical.

### 2. **Runtime Model Registration**
New models can be registered at runtime without modifying core code. This enables:
- External packages to provide model implementations
- Research-specific models without forking the codebase
- Easy testing with mock models

### 3. **Configuration-Driven Model Selection**
Models are selected via configuration, not code changes. The same analysis pipeline can use different models by simply changing the config file.

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  evaluate_impact │───▶│ ModelingEngine   │───▶│ ModelInterface  │
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
            │ Interrupted  │  │ Causal       │  │ Regression   │  │ Custom       │
            │ Time Series  │  │ Impact       │  │ Discontinuity│  │ Model        │
            └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

## Package Structure

```
impact_engine/modeling/
├── __init__.py                    # Public API exports
├── base.py                       # ModelInterface + common utilities
├── engine.py                     # ModelingEngine coordination logic
└── interrupted_time_series.py   # Built-in ITS implementation
```

**Design Rationale**: Each file has a single responsibility, making the codebase easier to navigate, test, and extend. The engine acts as a coordinator while models focus on their specific algorithms.

## Registration API

### Direct Registration
```python
from impact_engine.modeling import ModelingEngine

engine = ModelingEngine()
engine.register_model("causal_impact", CausalImpactModel)
```

**Why Direct Registration**: Simplest approach that covers 90% of use cases. No complex setup, no packaging requirements, immediate availability.

## Standardized Model Interface

All models implement the same interface:
```python
class ModelInterface(ABC):
    @abstractmethod
    def fit(self, data: pd.DataFrame, intervention_date: str, 
            output_path: str, **kwargs) -> str:
        """Fit model and return path to results file."""
        pass
    
    @abstractmethod
    def validate_data(self, data: pd.DataFrame) -> bool:
        """Validate input data meets model requirements."""
        pass
    
    @abstractmethod
    def get_required_columns(self) -> List[str]:
        """Return list of required data columns."""
        pass
```

**Design Rationale**: Consistent interface enables analysis code to work with any model. Model-specific logic happens within each implementation.

## Standardized Output Format

All models produce the same JSON output structure:
```json
{
  "model_type": "interrupted_time_series",
  "intervention_date": "2024-01-15",
  "dependent_variable": "revenue",
  "impact_estimates": {
    "intervention_effect": 1250.75,
    "pre_intervention_mean": 5000.0,
    "post_intervention_mean": 6250.75,
    "absolute_change": 1250.75,
    "percent_change": 25.015
  },
  "model_summary": {
    "n_observations": 365,
    "pre_period_length": 180,
    "post_period_length": 185,
    "aic": 4521.2,
    "bic": 4535.8
  }
}
```

**Benefits**:
- Consistent results format across all models
- Easy comparison between different modeling approaches
- Standardized downstream analysis and reporting

## Configuration Philosophy

Models are configured declaratively:
```json
{
  "model": {
    "type": "interrupted_time_series",
    "parameters": {
      "intervention_date": "2024-01-15",
      "dependent_variable": "revenue",
      "order": [1, 0, 0],
      "seasonal_order": [0, 0, 0, 0]
    }
  }
}
```

**Benefits**:
- Same analysis pipeline works with different models
- Model-specific parameters are isolated
- No code changes required to switch models
- Easy A/B testing of different modeling approaches

## Built-in Models

### Interrupted Time Series (ITS)
- **Purpose**: Causal impact analysis using time series intervention
- **Method**: SARIMAX with intervention dummy variable
- **Use Case**: Single intervention point with clear before/after periods
- **Required Data**: Time series with date and dependent variable

### Extension Points

#### For Model Authors
1. Implement `ModelInterface`
2. Handle model-specific fitting logic
3. Validate input data requirements
4. Produce standardized JSON output
5. Register with `ModelingEngine`

#### For Application Developers
1. Create configuration file with model parameters
2. Register custom models (if needed)
3. Call `evaluate_impact()` or use `ModelingEngine` directly

## Error Handling Strategy

- **Data Validation**: Fail fast with specific column/format requirements
- **Model Fitting**: Catch statistical errors, provide diagnostic information
- **Configuration Errors**: Validate early, provide parameter guidance
- **Output Generation**: Ensure consistent format even with partial results

## Performance Monitoring

The `ModelingEngine` tracks operation statistics:
```python
engine.get_operation_stats()
# Returns:
{
    'config_loads': 5,
    'model_fits': 12,
    'model_instantiations': 12,
    'total_fit_time': 45.2,
    'avg_fit_time': 3.77,
    'failed_operations': 1
}
```

**Benefits**: Performance monitoring helps identify bottlenecks and optimize model selection for production workloads.

## Debug and Logging

Enable detailed execution traces:
```python
engine = ModelingEngine(enable_debug_logging=True)
# Or enable later:
engine.enable_debug_logging()
```

**Use Cases**:
- Troubleshooting model fitting issues
- Performance optimization
- Understanding data flow through the pipeline

This approach ensures robust operation while providing clear feedback for development and production monitoring.