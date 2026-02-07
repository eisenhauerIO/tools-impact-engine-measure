# Backlog

## Open

## Done

- **Storage path should not be passed to ITS models**: Storage object was being passed to all model adapters via `fit(**kwargs)`. Decoupled by adding `artifacts` field to `ModelResult` — models now return supplementary DataFrames via artifacts, and `ModelsManager` handles all persistence centrally.