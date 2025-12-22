# User Stories

## Data Analysts

Measure the causal impact of product interventions on business metrics to provide evidence-based recommendations to stakeholders.

### Example Workflow

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

---

## Data Engineers

Integrate custom data sources with Impact Engine so that analysts can access company-specific metrics without modifying core code.

### Example Workflow

**1. Implement MetricsInterface**:

```python
from impact_engine.metrics import MetricsManager, MetricsInterface

class SalesforceAdapter(MetricsInterface):
    def connect(self, config):
        # Initialize connection to Salesforce
        return True

    def validate_connection(self):
        # Verify connection is active
        return True

    def retrieve_business_metrics(self, products, start_date, end_date):
        # Fetch metrics from Salesforce
        return metrics_df

    def transform_outbound(self, products, start_date, end_date):
        # Transform to Salesforce query format
        return query_params

    def transform_inbound(self, external_data):
        # Transform to standard schema
        return standardized_df
```

**2. Register adapter**:

```python
manager = MetricsManager(config)
manager.register_metrics("salesforce", SalesforceAdapter)
```

**3. Metrics data schema** (expected output format):

| Column | Type | Description |
|--------|------|-------------|
| `product_id` | str | Unique product identifier |
| `name` | str | Product name |
| `category` | str | Product category |
| `price` | float | Product price |
| `date` | datetime | Observation date |
| `sales_volume` | int | Number of units sold |
| `revenue` | float | Total revenue |
| `inventory_level` | int | Current inventory |
| `customer_engagement` | float | Engagement metric |
| `metrics_source` | str | Source identifier |
| `retrieval_timestamp` | datetime | When data was retrieved |

---

## Research Scientists

Implement custom statistical models to apply cutting-edge causal inference techniques to business problems.

### Example Workflow

**1. Implement Model interface**:

```python
from impact_engine.models import ModelsManager, Model

class CausalImpactModel(Model):
    def connect(self, config):
        # Initialize model with config
        return True

    def validate_connection(self):
        return True

    def validate_data(self, data):
        # Check data meets requirements
        return True

    def get_required_columns(self):
        return ['date', 'revenue']

    def transform_outbound(self, data, intervention_date, **kwargs):
        # Transform to model library format
        return transformed_data

    def transform_inbound(self, model_results):
        # Transform to standard output format
        return standardized_results

    def fit(self, data, intervention_date, output_path, **kwargs):
        # Fit model and save results
        return result_path
```

**2. Register model**:

```python
manager = ModelsManager(config)
manager.register_model("causal_impact", CausalImpactModel)
```

**3. Use in configuration**:

```yaml
MEASUREMENT:
  MODEL: causal_impact
  PARAMS:
    INTERVENTION_DATE: "2024-01-15"
    DEPENDENT_VARIABLE: revenue
```

---

## Product Managers

Quickly assess the impact of feature launches to make data-driven decisions about product development.

### Example Workflow

**1. Request analysis** from data team with:
- Intervention date (when the feature launched)
- Products affected
- Metric to measure (e.g., revenue, engagement)

**2. Review results**:

```yaml
impact_estimates:
  intervention_effect: 1250.75      # Revenue increase per day
  percent_change: 25.015            # 25% improvement
model_summary:
  pre_period_length: 180            # Days before launch
  post_period_length: 185           # Days after launch
```

**3. Key questions answered**:
- Did the intervention have a measurable effect?
- What is the magnitude of the impact?
- Is the effect statistically significant?
