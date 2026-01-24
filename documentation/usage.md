# Usage

## Basic Workflow

**1. Create configuration file** (`config.yaml`):

```yaml
DATA:
  TYPE: simulator
  PATH: data/products.csv
  MODE: rule
  SEED: 42
  START_DATE: "2024-01-01"
  END_DATE: "2024-01-31"

MEASUREMENT:
  MODEL: interrupted_time_series
  PARAMS:
    INTERVENTION_DATE: "2024-01-15"
    DEPENDENT_VARIABLE: revenue
```

**2. Run analysis**:

```python
from impact_engine import evaluate_impact

result_path = evaluate_impact(
    config_path='config.yaml',
    storage_url='results/'
)

print(f"Results saved to: {result_path}")
```

**3. Review results** (YAML output):

```yaml
model_type: interrupted_time_series
intervention_date: "2024-01-15"
dependent_variable: revenue
impact_estimates:
  intervention_effect: 1250.75
  pre_intervention_mean: 5000.0
  post_intervention_mean: 6250.75
  absolute_change: 1250.75
  percent_change: 25.015
model_summary:
  n_observations: 365
  pre_period_length: 180
  post_period_length: 185
```

## Extending Impact Engine

For custom metrics adapters or statistical models, see the [Architecture documentation](architecture.md).
