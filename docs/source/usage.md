# Usage

## Workflow

Every analysis follows the same three steps regardless of which measurement model is used.

**1. Prepare a product catalog.** Provide a CSV with product characteristics (`product_identifier`, `category`, `price`). In demo notebooks, the catalog simulator generates this automatically.

**2. Write a YAML configuration file.** The config has three sections: `DATA` selects the data source and optional transformations, `MEASUREMENT` selects the model and its parameters, and `OUTPUT` sets the storage path. See [Configuration](configuration.md) for the full parameter reference.

```yaml
DATA:
  SOURCE:
    type: simulator
    CONFIG:
      path: data/products.csv
      start_date: "2024-01-01"
      end_date: "2024-01-31"
  TRANSFORM:
    FUNCTION: aggregate_by_date
    PARAMS:
      metric: revenue

MEASUREMENT:
  MODEL: interrupted_time_series
  PARAMS:
    intervention_date: "2024-01-15"
    dependent_variable: revenue

OUTPUT:
  PATH: output
```

**3. Run the analysis.**

```python
from impact_engine_measure import evaluate_impact

results_path = evaluate_impact(
    config_path="config.yaml",
    storage_url="./results"
)
```

The engine loads products, retrieves metrics, applies transformations, fits the model, and writes results. The return value is the path to `impact_results.json`.

---

## Output

Every run produces a standardized output regardless of which model was used.

**`impact_results.json`** contains the result envelope:

```json
{
  "schema_version": "2.0",
  "model_type": "<model_name>",
  "data": {
    "model_params": { },
    "impact_estimates": { },
    "model_summary": { }
  },
  "metadata": {
    "executed_at": "2026-02-08T12:00:00+00:00"
  }
}
```

The three keys inside `data` are standardized across all models. `model_params` echoes the input parameters. `impact_estimates` holds the treatment effect measurements. `model_summary` provides fit diagnostics and sample sizes.

**`manifest.json`** lists all output files and their formats, making the output self-describing. Consumers should read the manifest to resolve file paths rather than hardcoding filenames.

Some models produce **supplementary artifacts** as Parquet files (e.g., per-stratum breakdowns, matched data). These are listed in the manifest and named `{model_type}__{artifact_name}.parquet`.

---

## Available Models

Each model has a demo notebook with a runnable end-to-end example including truth recovery validation and convergence analysis.

| Model | Library | Interface | Description | Demo |
|-------|---------|-----------|-------------|------|
| Experiment | [statsmodels](https://www.statsmodels.org/) | [`ols()`](https://www.statsmodels.org/stable/generated/statsmodels.formula.api.ols.html) | Linear regression for randomized A/B tests | [demo_experiment](models/demo_experiment) |
| Interrupted Time Series | [statsmodels](https://www.statsmodels.org/) | [`SARIMAX()`](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.html) | ARIMA-based pre/post intervention comparison on aggregated time series | [demo_interrupted_time_series](models/demo_interrupted_time_series) |
| Nearest Neighbour Matching | [causalml](https://causalml.readthedocs.io/) | [`NearestNeighborMatch`](https://causalml.readthedocs.io/en/latest/methodology.html#matching) | Causal matching on covariates for ATT/ATC estimation | [demo_nearest_neighbour_matching](models/demo_nearest_neighbour_matching) |
| Subclassification | [pandas](https://pandas.pydata.org/) / [NumPy](https://numpy.org/) | `qcut()` + `np.average()` | Propensity stratification with within-stratum treatment effects | [demo_subclassification](models/demo_subclassification) |
| Synthetic Control | [pysyncon](https://github.com/sdfordham/pysyncon) | [`Synth`](https://sdfordham.github.io/pysyncon/synth.html) | Synthetic control method for aggregate intervention analysis | [demo_synthetic_control](models/demo_synthetic_control) |
| Metrics Approximation | *(built-in)* | Response function registry | Response function approximation using a library of candidate functions | [demo_metrics_approximation](models/demo_metrics_approximation) |
