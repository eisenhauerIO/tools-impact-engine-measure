# Configuration Reference

This document describes all configuration options for Impact Engine.

## Configuration File Structure

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

### Simulator CONFIG Parameters

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
        FUNCTION: quantity_boost
        PARAMS:
          effect_size: 0.3
          enrichment_fraction: 1.0
          enrichment_start: "2024-11-23"
          seed: 42
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ENRICHMENT.FUNCTION` | string | Yes | Enrichment function: `"quantity_boost"` |
| `ENRICHMENT.PARAMS.effect_size` | float | Yes | Magnitude of the intervention effect (e.g., 0.3 = 30% boost) |
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
