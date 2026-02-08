# Design Philosophy

## Models: Thin Wrappers

Each measurement model adapter should be as thin a wrapper as possible around the underlying Python library. Minimize custom logic; delegate to the library for all statistical/ML work. The adapter's job is only to translate between the impact engine's interface (config, DataFrame in, ModelResult out) and the library's API.

## Model Output

### Schema Version

All output files include a `schema_version` field (currently `"2.0"`) to enable forward-compatible parsing by consumers.

### JSON Envelope (`impact_results.json`)

Every model returns a `ModelResult`; the manager persists it via `storage.write_json("impact_results.json", result.to_dict())`. The serialized JSON has a **stable envelope**:

```json
{
  "schema_version": "2.0",
  "model_type": "<model_name>",
  "data": {
    "model_params": { ... },
    "impact_estimates": { ... },
    "model_summary": { ... }
  },
  "metadata": {
    "executed_at": "2026-02-08T12:00:00+00:00"
  }
}
```

The three keys inside `data` are standardized across all models:

- **`model_params`**: Input parameters used for this run (formula, intervention_date, response_function, etc.). Model-specific.
- **`impact_estimates`**: The treatment effect measurements. Model-specific keys, but this is always the primary result.
- **`model_summary`**: Fit diagnostics, sample sizes, and configuration echo (rsquared, nobs, n_strata, etc.).

Models never write the main result file themselves. The manager handles serialization and storage.

### Supplementary Artifacts (Parquet)

When a model needs to persist detailed row-level data (e.g., per-product impacts, per-stratum breakdowns), it returns DataFrames in `ModelResult.artifacts`. The manager writes them as Parquet files.

**Naming convention**: Artifact files are prefixed with the model type using double-underscore separation:

```
{model_type}__{artifact_name}.parquet
```

Examples:
- `subclassification__stratum_details.parquet`
- `nearest_neighbour_matching__matched_data_att.parquet`
- `nearest_neighbour_matching__balance_before.parquet`
- `metrics_approximation__product_level_impacts.parquet`

This prevents collisions with pipeline-level files and makes artifacts self-identifying.

### Job Manifest (`manifest.json`)

Every pipeline run writes a `manifest.json` as its final step. This makes the output **self-describing** — consumers read the manifest first, then load exactly what they need.

```json
{
  "schema_version": "2.0",
  "model_type": "nearest_neighbour_matching",
  "created_at": "2026-02-08T12:00:00+00:00",
  "files": {
    "config": {"path": "config.yaml", "format": "yaml"},
    "products": {"path": "products.parquet", "format": "parquet"},
    "business_metrics": {"path": "business_metrics.parquet", "format": "parquet"},
    "transformed_metrics": {"path": "transformed_metrics.parquet", "format": "parquet"},
    "impact_results": {"path": "impact_results.json", "format": "json"},
    "nearest_neighbour_matching__matched_data_att": {"path": "nearest_neighbour_matching__matched_data_att.parquet", "format": "parquet"}
  }
}
```

### `FitOutput` Return Type

`ModelsManager.fit_model()` returns a `FitOutput` dataclass (not a plain string path). This provides programmatic access to:
- `results_path`: Full path to `impact_results.json`
- `artifact_paths`: Dict mapping artifact names to their full paths
- `model_type`: Which model produced the output

### Metadata

The manager populates `ModelResult.metadata` with execution context (timestamp). Models never set metadata themselves.

## Output Directory Structure

Current layout (flat):

```
job-impact-engine-XXXX/
  config.yaml
  manifest.json
  products.parquet
  business_metrics.parquet
  transformed_metrics.parquet
  impact_results.json
  {model_type}__{artifact_name}.parquet
```

Future consideration: split into `pipeline/` and `model/` subdirectories. Consumers should use `manifest.json` to resolve paths rather than hardcoding filenames, to make future reorganization non-breaking.
