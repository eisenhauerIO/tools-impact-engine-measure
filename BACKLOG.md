# Backlog: impact-engine-measure

Prioritized work queue for package improvements. See DESIGN.md for
architectural context.

## Current state

The package provides `measure_impact()` with six pluggable model adapters,
pluggable metrics and storage layers, normalized `measure_result.json`
output, and `load_results()` for structured access to job output.

## Open

## Done

- **`load_results()` API**: `measure_impact()` returns `JobInfo`; `load_results(job_info)` loads all artifacts into a typed `MeasureJobResult`.

- **Storage path should not be passed to ITS models**: Storage object was being passed to all model adapters via `fit(**kwargs)`. Decoupled by adding `artifacts` field to `ModelResult` — models now return supplementary DataFrames via artifacts, and `ModelsManager` handles all persistence centrally.
