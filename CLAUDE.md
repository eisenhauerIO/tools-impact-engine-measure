# CLAUDE.md

## Project overview

Causal impact measurement for the impact engine pipeline. Runs econometric models
(experiment, synthetic control, nearest-neighbour matching, interrupted time series,
subclassification, metrics approximation) against product data and writes normalized
results to a job directory for downstream pipeline stages.

## Development setup

```bash
pip install hatch
hatch env create
```

## Common commands

- `hatch run test` — run pytest suite
- `hatch run lint` — check with ruff
- `hatch run format` — auto-format with ruff
- `hatch run docs:build` — build Sphinx documentation

Always use `hatch run` to execute commands. Never bare `python` or `pytest`.

## Architecture

- `impact_engine_measure/engine.py` — `measure_impact()`: main entry point; orchestrates config, model, storage
- `impact_engine_measure/config.py` — `parse_config_file()` (internal); `load_config()` re-exported as canonical entry point
- `impact_engine_measure/normalize.py` — `normalize_result()`: writes `measure_result.json` (flat normalized estimates)
- `impact_engine_measure/results.py` — `MeasureJobResult`, `load_results()`: structured access to job output
- `impact_engine_measure/core/validation.py` — `load_config()`: parse-once config entry point
- `impact_engine_measure/core/contracts.py` — internal data contracts
- `impact_engine_measure/core/transforms.py` — shared data transformations
- `impact_engine_measure/metrics/` — `MetricsManager`, `MetricsInterface`, `METRICS_REGISTRY`: pluggable metric definitions
- `impact_engine_measure/models/` — `ModelsManager`, `ModelInterface`, `MODEL_REGISTRY`: pluggable model adapters
  - `experiment/` — OLS-based experiment adapter
  - `synthetic_control/` — synthetic control adapter (pysyncon)
  - `nearest_neighbour_matching/` — PSM adapter (causalml)
  - `interrupted_time_series/` — ITS adapter (statsmodels)
  - `subclassification/` — subclassification adapter
  - `metrics_approximation/` — metrics approximation adapter
- `impact_engine_measure/storage/` — job directory I/O
- `tests/` — unit and integration tests
- `docs/source/` — Sphinx docs with method demo notebooks

## Verification

1. `hatch run lint` — confirm no ruff errors
2. `hatch run test` — all tests pass
3. `hatch run docs:build` — docs build without warnings

## Key conventions

- NumPy-style docstrings
- Logging via `logging.getLogger(__name__)` (no print statements)
- Models are thin wrappers — delegate all statistical work to the underlying library
- Every model run writes `measure_result.json` (normalized flat dict) and `manifest.json`; consumers read these files, not raw model output
- `_external/` contains reference submodules — do not modify
