## Development

Always use the hatch environment for running tests, linting, and other dev tasks:
- Run tests: `hatch run test`
- Format: `hatch run format`
- Lint: `hatch run lint`

Never use bare `pytest`, `black`, or `ruff` directly — always go through `hatch run`.

## Design Philosophy

### Models: Thin Wrappers

Each measurement model adapter should be as thin a wrapper as possible around the underlying Python library. Minimize custom logic; delegate to the library for all statistical/ML work. The adapter's job is only to translate between the impact engine's interface (config, DataFrame in, ModelResult out) and the library's API.

### Model Output

All output files include a `schema_version` field (currently `"2.0"`) to enable forward-compatible parsing by consumers.

**JSON Envelope (`impact_results.json`).** Every model returns a `ModelResult`; the manager persists it via `storage.write_json("impact_results.json", result.to_dict())`. The serialized JSON has a stable envelope with three standardized keys inside `data`:

- **`model_params`**: Input parameters used for this run. Model-specific.
- **`impact_estimates`**: The treatment effect measurements. Model-specific keys, but always the primary result.
- **`model_summary`**: Fit diagnostics, sample sizes, and configuration echo.

Models never write the main result file themselves. The manager handles serialization and storage.

**Supplementary Artifacts (Parquet).** When a model needs to persist detailed row-level data, it returns DataFrames in `ModelResult.artifacts`. The manager writes them as Parquet files named `{model_type}__{artifact_name}.parquet`.

**Job Manifest (`manifest.json`).** Every pipeline run writes a manifest as its final step, making the output self-describing. Consumers read the manifest first, then load exactly what they need.

**`FitOutput` Return Type.** `ModelsManager.fit_model()` returns a `FitOutput` dataclass providing programmatic access to `results_path`, `artifact_paths`, and `model_type`.

**Metadata.** The manager populates `ModelResult.metadata` with execution context (timestamp). Models never set metadata themselves.

### Output Directory Structure

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

## Skills & Subagents

### General (shared across projects)
- Skills: .claude/general-skills/
- Subagents: .claude/general-subagents/

### Project-specific
- Skills: .claude/skills/

To invoke a subagent, read its .md file and follow its instructions.
General resources take precedence unless a project-specific skill covers the same topic.