# Backlog

## Open

## Done

- **`load_results()` API**: `evaluate_impact()` returns `JobInfo`; `load_results(job_info)` loads all artifacts into a typed `MeasureJobResult`.

- **Storage path should not be passed to ITS models**: Storage object was being passed to all model adapters via `fit(**kwargs)`. Decoupled by adding `artifacts` field to `ModelResult` — models now return supplementary DataFrames via artifacts, and `ModelsManager` handles all persistence centrally.
