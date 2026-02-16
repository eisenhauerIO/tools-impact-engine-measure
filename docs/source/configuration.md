# Configuration

Impact Engine uses YAML configuration files to control all aspects of data sourcing, measurement, and output. This guide documents the **actual configuration schema** as implemented in the code.

> **See Also**: For practical examples, see the [Model demo notebooks](models/demo_interrupted_time_series.ipynb).

## Configuration Structure

Impact Engine uses YAML configuration files with three main sections:

```yaml
DATA:
  SOURCE:
    # Data source configuration
  TRANSFORM:
    # Optional data transformation

MEASUREMENT:
  # Model configuration

OUTPUT:
  # Output path configuration
```

## DATA Section

Configures where metrics data comes from and how it's transformed.

### SOURCE Configuration

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `type` | string | No | Data source type: `"simulator"` (default) |
| `CONFIG` | object | Yes | Source-specific configuration |

### Simulator CONFIG Parameters (default)

The simulator generates synthetic metrics data from a product catalog.

```yaml
DATA:
  SOURCE:
    type: simulator
    CONFIG:
      mode: rule
      seed: 42
      path: data/products.csv
      start_date: "2024-01-01"
      end_date: "2024-01-31"
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `path` | string | Yes | - | Path to products CSV file |
| `start_date` | string | Yes | - | Analysis start date (YYYY-MM-DD) |
| `end_date` | string | Yes | - | Analysis end date (YYYY-MM-DD) |
| `mode` | string | No | `"rule"` | Simulation mode: `"rule"` (deterministic) |
| `seed` | int | No | `42` | Random seed for reproducibility |

### File CONFIG Parameters

Load metrics from an existing CSV or Parquet file instead of simulating.

```yaml
DATA:
  SOURCE:
    type: file
    CONFIG:
      path: data/metrics.csv
      product_id_column: product_id
      date_column: date
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `path` | string | Yes | - | Path to data file (CSV, Parquet, or partitioned Parquet directory) |
| `product_id_column` | string | No | `"product_id"` | Column name for product identifiers |
| `date_column` | string | No | `"date"` | Column name for dates |

### Enrichment Configuration

Apply synthetic interventions to simulated data for testing causal impact detection.

```yaml
DATA:
  SOURCE:
    type: simulator
    CONFIG:
      mode: rule
      seed: 42
      path: data/products.csv
      start_date: "2024-11-01"
      end_date: "2024-12-15"
  ENRICHMENT:
    FUNCTION: product_detail_boost
    PARAMS:
      quality_boost: 0.15
      enrichment_fraction: 1.0
      enrichment_start: "2024-11-23"
      seed: 42
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ENRICHMENT.FUNCTION` | string | Yes | Enrichment function: `"product_detail_boost"` |
| `ENRICHMENT.PARAMS.quality_boost` | float | Yes | Magnitude of the quality score boost (e.g., 0.15) |
| `ENRICHMENT.PARAMS.enrichment_fraction` | float | No | Fraction of products to enrich (0.0-1.0, default 1.0) |
| `ENRICHMENT.PARAMS.enrichment_start` | string | Yes | Date when enrichment begins (YYYY-MM-DD) |
| `ENRICHMENT.PARAMS.seed` | int | No | Random seed for reproducibility |

### TRANSFORM Configuration

Optional transformation applied to data before model fitting.

```yaml
DATA:
  TRANSFORM:
    FUNCTION: aggregate_by_date
    PARAMS:
      metric: revenue
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `FUNCTION` | string | No | `"passthrough"` | Transform function name |
| `PARAMS` | object | No | `{}` | Function-specific parameters |

#### Available Transforms

Each model typically pairs with a specific transform. The engine selects the transform by name from a registry.

| Transform | Used With | Description | Key Parameters |
|-----------|-----------|-------------|----------------|
| `passthrough` | Any | No-op default. Passes data through unchanged. | None |
| `aggregate_by_date` | Interrupted Time Series | Sums all numeric columns by date, producing one row per date. | `metric`: column to validate exists (default `"revenue"`) |
| `prepare_for_synthetic_control` | Synthetic Control | Adds a `treatment` column derived from enrichment status and date. | `enrichment_start`: date when enrichment began (auto-injected from ENRICHMENT.PARAMS) |
| `aggregate_for_approximation` | Metrics Approximation | Aggregates baseline metric per product into cross-sectional format. | `baseline_metric`: column to aggregate (default `"revenue"`) |
| `prepare_simulator_for_approximation` | Metrics Approximation (simulator source) | Converts simulator time-series into before/after quality scores and baseline sales per product. | `enrichment_start`: date split point (required), `baseline_metric`: column to aggregate (default `"revenue"`) |

## MEASUREMENT Section

Configures the statistical model for impact analysis.

### Common Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `MODEL` | string | No | Model type (default: `"interrupted_time_series"`) |
| `PARAMS` | object | Yes | Model-specific parameters |

### Interrupted Time Series Model

```yaml
MEASUREMENT:
  MODEL: interrupted_time_series
  PARAMS:
    intervention_date: "2024-01-15"
    dependent_variable: revenue
    order: [1, 0, 0]
    seasonal_order: [0, 0, 0, 0]
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `intervention_date` | string | Yes | - | Date when intervention occurred (YYYY-MM-DD) |
| `dependent_variable` | string | No | `"revenue"` | Column name to analyze |
| `order` | array | No | `[1, 0, 0]` | ARIMA order (p, d, q) |
| `seasonal_order` | array | No | `[0, 0, 0, 0]` | Seasonal ARIMA order (P, D, Q, s) |

### Experiment Model

```yaml
MEASUREMENT:
  MODEL: experiment
  PARAMS:
    formula: "revenue ~ treatment + price"
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `formula` | string | Yes | - | R-style formula where all variables must exist in the DataFrame |

---

### Subclassification Model

```yaml
MEASUREMENT:
  MODEL: subclassification
  PARAMS:
    dependent_variable: revenue
    treatment_column: treatment
    covariate_columns:
      - price
    n_strata: 5
    estimand: att
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `dependent_variable` | string | No | `"revenue"` | Outcome column name |
| `treatment_column` | string | Yes | - | Binary treatment indicator column |
| `covariate_columns` | list | Yes | - | Columns used for propensity stratification |
| `n_strata` | int | No | `5` | Number of quantile-based strata |
| `estimand` | string | No | `"att"` | Estimand: `"att"` or `"ate"` |

---

### Nearest Neighbour Matching Model

```yaml
MEASUREMENT:
  MODEL: nearest_neighbour_matching
  PARAMS:
    dependent_variable: revenue
    treatment_column: treatment
    covariate_columns:
      - price
    caliper: 0.2
    replace: false
    ratio: 1
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `dependent_variable` | string | No | `"revenue"` | Outcome column name |
| `treatment_column` | string | Yes | - | Binary treatment indicator column |
| `covariate_columns` | list | Yes | - | Columns used for matching |
| `caliper` | float | No | `0.2` | Maximum distance for a valid match |
| `replace` | bool | No | `false` | Whether to match with replacement |
| `ratio` | int | No | `1` | Number of matches per unit |
| `shuffle` | bool | No | `true` | Shuffle data before matching |
| `random_state` | int | No | `null` | Random seed for reproducibility |
| `n_jobs` | int | No | `1` | Number of parallel jobs |

---

### Metrics Approximation Model

```yaml
MEASUREMENT:
  MODEL: metrics_approximation
  PARAMS:
    metric_before_column: quality_before
    metric_after_column: quality_after
    baseline_column: baseline_sales
    RESPONSE:
      FUNCTION: linear
      PARAMS:
        coefficient: 0.5
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `metric_before_column` | string | No | `"quality_before"` | Column name for pre-intervention metric |
| `metric_after_column` | string | No | `"quality_after"` | Column name for post-intervention metric |
| `baseline_column` | string | No | `"baseline_sales"` | Column name for baseline outcome |
| `RESPONSE.FUNCTION` | string | No | `"linear"` | Response function name from the response registry |
| `RESPONSE.PARAMS.coefficient` | float | No | `0.5` | Coefficient for the linear response function |

---

### Synthetic Control Model

```yaml
MEASUREMENT:
  MODEL: synthetic_control
  PARAMS:
    treatment_time: 15
    treated_unit: "unit_A"
    outcome_column: revenue
    unit_column: unit_id
    time_column: date
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `treatment_time` | int | Yes | - | Time index when intervention occurred |
| `treated_unit` | string | Yes | - | Name of the treated unit |
| `outcome_column` | string | Yes | - | Column with the outcome variable |
| `unit_column` | string | No | `"unit_id"` | Column identifying units |
| `time_column` | string | No | `"date"` | Column identifying time periods |
| `optim_method` | string | No | `"Nelder-Mead"` | Optimization method passed to pysyncon |
| `optim_initial` | string | No | `"equal"` | Initial weight strategy for optimization |

---

## OUTPUT Section

Configures where results are stored.

```yaml
OUTPUT:
  PATH: output
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `PATH` | string | No | `"output"` | Directory for output files |

## Complete Example

```yaml
DATA:
  SOURCE:
    type: simulator
    CONFIG:
      mode: rule
      seed: 42
      path: data/products.csv
      start_date: "2024-01-01"
      end_date: "2024-03-31"
  TRANSFORM:
    FUNCTION: aggregate_by_date
    PARAMS:
      metric: revenue

MEASUREMENT:
  MODEL: interrupted_time_series
  PARAMS:
    intervention_date: "2024-02-01"
    dependent_variable: revenue
    order: [1, 0, 0]
    seasonal_order: [0, 0, 0, 7]

OUTPUT:
  PATH: output
```

## Next Steps

- **Examples**: See the [Model demo notebooks](models/demo_interrupted_time_series.ipynb) for practical examples
- **API**: See [API Reference](api_reference.rst) for function documentation
- **Design**: See [Design](design.md) for system internals
