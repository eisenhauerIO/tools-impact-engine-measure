# Configuration Reference

This document describes all configuration options for Impact Engine.

## Configuration File Structure

Impact Engine uses YAML configuration files with two main sections:

```yaml
DATA:
  # Data source configuration

MEASUREMENT:
  # Model configuration
```

## DATA Section

Configures where metrics data comes from.

### Common Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `TYPE` | string | Yes | Data source type: `"simulator"` |
| `PATH` | string | Yes | Path to products CSV file |
| `START_DATE` | string | Yes | Analysis start date (YYYY-MM-DD) |
| `END_DATE` | string | Yes | Analysis end date (YYYY-MM-DD) |

### Simulator Configuration

Use the built-in catalog simulator for testing and development.

```yaml
DATA:
  TYPE: simulator
  PATH: data/products.csv
  MODE: rule
  SEED: 42
  START_DATE: "2024-01-01"
  END_DATE: "2024-01-31"
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `MODE` | string | `"rule"` | Simulation mode: `"rule"` (deterministic) or `"ml"` (ML-based) |
| `SEED` | int | `42` | Random seed for reproducibility |

### Enrichment Configuration

Apply synthetic interventions to simulated data for testing causal impact detection.

```yaml
DATA:
  TYPE: simulator
  PATH: data/products.csv
  MODE: rule
  SEED: 42
  START_DATE: "2024-11-01"
  END_DATE: "2024-12-15"
  ENRICHMENT:
    function: quantity_boost
    params:
      effect_size: 0.3
      enrichment_fraction: 1.0
      enrichment_start: "2024-11-23"
      seed: 42
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ENRICHMENT.function` | string | Yes | Enrichment function: `"quantity_boost"` |
| `ENRICHMENT.params.effect_size` | float | Yes | Magnitude of the intervention effect (e.g., 0.3 = 30% boost) |
| `ENRICHMENT.params.enrichment_fraction` | float | No | Fraction of products to enrich (0.0-1.0, default 1.0) |
| `ENRICHMENT.params.enrichment_start` | string | Yes | Date when enrichment begins (YYYY-MM-DD) |
| `ENRICHMENT.params.seed` | int | No | Random seed for reproducibility |

## MEASUREMENT Section

Configures the statistical model for impact analysis.

### Common Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `MODEL` | string | Yes | Model type: `"interrupted_time_series"` |
| `PARAMS` | object | Yes | Model-specific parameters |

### Interrupted Time Series Model

```yaml
MEASUREMENT:
  MODEL: interrupted_time_series
  PARAMS:
    INTERVENTION_DATE: "2024-01-15"
    DEPENDENT_VARIABLE: revenue
    order: [1, 0, 0]
    seasonal_order: [0, 0, 0, 0]
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `INTERVENTION_DATE` | string | Yes | - | Date when intervention occurred (YYYY-MM-DD) |
| `DEPENDENT_VARIABLE` | string | No | `"revenue"` | Column name to analyze |
| `order` | array | No | `[1, 0, 0]` | ARIMA order (p, d, q) |
| `seasonal_order` | array | No | `[0, 0, 0, 0]` | Seasonal ARIMA order (P, D, Q, s) |

## Complete Example

```yaml
DATA:
  TYPE: simulator
  PATH: data/products.csv
  MODE: rule
  SEED: 42
  START_DATE: "2024-01-01"
  END_DATE: "2024-03-31"

MEASUREMENT:
  MODEL: interrupted_time_series
  PARAMS:
    INTERVENTION_DATE: "2024-02-01"
    DEPENDENT_VARIABLE: revenue
    order: [1, 0, 0]
    seasonal_order: [0, 0, 0, 7]
```
