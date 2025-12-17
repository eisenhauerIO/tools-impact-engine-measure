# Models Layer Architecture

## Design Philosophy

The models layer follows a **unified interface architecture** with three core principles:

### 1. **Consistent Model Interface**
All models implement the same `Model` interface, ensuring uniform behavior regardless of the underlying statistical approach. Whether using interrupted time series, causal inference, or regression discontinuity, the interface remains identical.

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
│  engine.py      │───▶│ ModelsManager    │───▶│ Model           │
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
            │ Interrupted  │  │ Causal       │  │ Regression   │  │ Custom       │
            │ Time Series  │  │ Impact       │  │ Discontinuity│  │ Model        │
            │ Adapter      │  │ Adapter      │  │ Adapter      │  │ Adapter      │
            └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

## Package Structure

```
impact_engine/
├── engine.py                    # Main orchestration engine
├── models/
│   ├── __init__.py             # Public API exports
│   ├── base.py                 # Model interface + common utilities
│   ├── manager.py              # ModelsManager coordination logic
│   └── adapter_interrupted_time_series.py  # Built-in ITS implementation
└── metrics/
    ├── __init__.py             # Public API exports
    ├── base.py                 # MetricsInterface + common utilities
    ├── manager.py              # MetricsManager coordination logic
    └── adapter_catalog_simulator.py  # Built-in simulator implementation
```

**Design Rationale**: Each file has a single responsibility, making the codebase easier to navigate, test, and extend. The manager acts as a coordinator while model adapters focus on their specific algorithms.

## Registration API

### Direct Registration
```python
from impact_engine.models import ModelsManager

manager = ModelsManager(config)
manager.register_model("causal_impact", CausalImpactModelAdapter)
```

**Why Direct Registration**: Simplest approach that covers 90% of use cases. No complex setup, no packaging requirements, immediate availability.

## Standardized Model Interface

All models implement the same interface with connection and transformation methods:
```python
class Model(ABC):
    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> bool:
        """Initialize model with configuration parameters."""
        pass
    
    @abstractmethod
    def validate_connection(self) -> bool:
        """Validate that the model is properly initialized."""
        pass
    
    @abstractmethod
    def transform_outbound(self, data: pd.DataFrame, intervention_date: str, **kwargs) -> Dict[str, Any]:
        """Transform impact engine format to model library format."""
        pass
    
    @abstractmethod
    def transform_inbound(self, model_results: Any) -> Dict[str, Any]:
        """Transform model library results to impact engine format."""
        pass
    
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

**Design Rationale**: Consistent interface with explicit transformation methods enables analysis code to work with any model while maintaining clean separation between impact engine format and model library formats.

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

**Benefits**:
- Same analysis pipeline works with different models
- Model-specific parameters are isolated in PARAMS
- No code changes required to switch models
- Easy A/B testing of different modeling approaches
- Clear separation between data and measurement configuration

## Built-in Models

### Interrupted Time Series (ITS)
- **Purpose**: Causal impact analysis using time series intervention
- **Method**: SARIMAX with intervention dummy variable
- **Use Case**: Single intervention point with clear before/after periods
- **Required Data**: Time series with date and dependent variable

### Extension Points

#### For Model Authors
1. Implement `Model` interface
2. Implement `connect()` and `validate_connection()` methods
3. Implement `transform_outbound()` and `transform_inbound()` methods
4. Handle model-specific fitting logic
5. Validate input data requirements
6. Produce standardized JSON output
7. Register with `ModelsManager`

#### For Application Developers
1. Create configuration file with model parameters
2. Register custom models (if needed)
3. Call `evaluate_impact()` from `engine.py` or use `ModelsManager` directly

## Error Handling Strategy

- **Data Validation**: Fail fast with specific column/format requirements
- **Model Fitting**: Catch statistical errors, provide diagnostic information
- **Configuration Errors**: Validate early, provide parameter guidance
- **Output Generation**: Ensure consistent format even with partial results

## Usage Example

### Basic Usage
```python
from impact_engine import evaluate_impact
import pandas as pd

# Define products to analyze
products = pd.DataFrame({
    'product_id': ['prod1', 'prod2'],
    'name': ['Product 1', 'Product 2']
})

# Run impact analysis
result_path = evaluate_impact(
    config_path='config.json',
    products=products,
    output_path='results/'
)

print(f"Results saved to: {result_path}")
```

### Advanced Usage with Direct Manager Access
```python
from impact_engine.models import ModelsManager
from impact_engine.metrics import MetricsManager

# Initialize managers
metrics_manager = MetricsManager.from_config_file('config.json')
models_manager = ModelsManager.from_config_file('config.json')

# Retrieve metrics
business_metrics = metrics_manager.retrieve_metrics(products)

# Fit model
result_path = models_manager.fit_model(
    data=business_metrics,
    output_path='results/'
)
```

### Custom Model Registration
```python
from impact_engine.models import ModelsManager, Model

class CustomModel(Model):
    def connect(self, config):
        # Initialize model
        return True
    
    def transform_outbound(self, data, intervention_date, **kwargs):
        # Transform to model format
        return transformed_data
    
    def transform_inbound(self, model_results):
        # Transform to standard format
        return standardized_results
    
    # ... implement other required methods

# Register and use
manager = ModelsManager(config)
manager.register_model("custom", CustomModel)
```

This approach ensures robust operation while providing clear feedback for development and production monitoring.