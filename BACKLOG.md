# Backlog

## Open

- **`load_results(job_id)` API**: Add a function to retrieve results by job ID after execution, enabling workflow integrations to consume results without tracking file paths.

## Done

- **Storage path should not be passed to ITS models**: Storage object was being passed to all model adapters via `fit(**kwargs)`. Decoupled by adding `artifacts` field to `ModelResult` — models now return supplementary DataFrames via artifacts, and `ModelsManager` handles all persistence centrally.
