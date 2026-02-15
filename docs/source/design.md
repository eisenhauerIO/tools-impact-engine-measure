# Design

*Last updated: January 2026*

## Overview

Impact Engine measures the causal impact of interventions on business metrics. It answers questions like "Did this change improve our outcomes?" by comparing treatment and control groups using time-series analysis, metric approximations, and observational and causal models.

The architecture is **adapter-based**. Data sources, models, and storage backends are all pluggable. New adapters slot in without modifying the core engine or changing the user-facing API. The "Custom..." entries in the diagram below mark these extension points.

<p align="center">
  <img src="_static/diagrams/overview.svg" alt="Overview">
</p>

---

## Extensibility

The **plugin architecture** exists for a practical reason. Business settings often involve proprietary data sources and specialized modeling needs that can't be open-sourced. The adapter pattern lets these custom implementations live in private repositories while still integrating cleanly with the core engine. Custom adapters drop in without duplicating shared logic—they implement only what's unique and inherit everything else.

Two patterns make this work.

**Adapter pattern**. Each extension point implements a common interface defined in [MetricsInterface](../impact_engine_measure/metrics/base.py), [ModelInterface](../impact_engine_measure/models/base.py), and [StorageInterface](../impact_engine_measure/storage/base.py). The core engine calls interface methods without knowing which specific adapter is behind them. This keeps the core decoupled from implementation details. To add a new adapter, implement the relevant interface and register with its registry ([metrics](../impact_engine_measure/metrics/factory.py), [models](../impact_engine_measure/models/factory.py), or [storage](../impact_engine_measure/storage/factory.py)). All three use decorator-based self-registration, so there's no central file to modify.

**Data contracts**. The [Schema system](../impact_engine_measure/core/contracts.py) maps external column names to the engine's standard schema. Each data source defines its mappings once in a single place. The contract handles translation automatically, and the rest of the system works unchanged.

---

## Data Flow

The system is **configuration-driven**. A single config file selects which adapters to use, and data flows through four stages orchestrated by [engine.py](../impact_engine_measure/engine.py).

<p align="center">
  <img src="_static/diagrams/architecture.svg" alt="Data Flow">
</p>

Each stage is handled by a dedicated manager that delegates to the configured adapter.

```yaml
DATA:
  # ── Load ────────────────────────────────────────────────────
  SOURCE:
    TYPE: simulator                     # metrics adapter
    CONFIG:
      path: data/products.csv
      start_date: '2024-01-01'
      end_date: '2024-01-31'

  # ── Transform ────────────────────────────────────────────────────
  TRANSFORM:
    FUNCTION: aggregate_by_date
    PARAMS:
      metric: revenue

# ── Measure ────────────────────────────────────────────────────────
MEASUREMENT:
  MODEL: interrupted_time_series        # model adapter
  PARAMS:
    dependent_variable: revenue
    intervention_date: '2024-01-15'

# ── Store ──────────────────────────────────────────────────────────
OUTPUT:
  PATH: s3://bucket/results/campaign    # storage adapter
```

The config maps directly to the four stages. **Load** uses `DATA.SOURCE.TYPE` to select the metrics adapter. **Transform** applies `DATA.TRANSFORM.FUNCTION` to reshape data. **Measure** uses `MEASUREMENT.MODEL` to run causal analysis. **Store** writes results to `OUTPUT.PATH`—the backend is inferred from the path prefix.

---

## Engineering Practices

The codebase enforces quality through automated tooling. [GitHub Actions](https://github.com/features/actions) runs tests and linting on every push. [Ruff](https://docs.astral.sh/ruff/) handles fast linting and formatting. [pre-commit](https://pre-commit.com/) hooks catch issues locally, and type hints throughout enable static analysis.

The architecture facilitates testing through **dependency injection**. Each manager receives its adapter through the constructor rather than creating it internally, so [unit tests](../impact_engine_measure/tests/) can inject mock implementations that satisfy the interface contract. This means tests run fast and deterministically without requiring external systems. The same pattern applies across all three layers—metrics, models, and storage—making the entire codebase testable in isolation.

For complete configuration schema and parameter documentation, see the [Configuration Guide](configuration.md).
