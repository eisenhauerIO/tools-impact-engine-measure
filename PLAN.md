# Plan: `load_results` API (simulator-style)

## Context

The measure repo's `evaluate_impact()` writes self-describing job directories but provides no way to read them back, and returns a raw path string that's awkward to work with. The goal is to match the online-retail-simulator's concise pattern:

```python
# Simulator pattern (reference)
job_info = simulate(config_path)
results = load_job_results(job_info)

# Measure pattern (target)
job_info = evaluate_impact(config_path, storage_url="./data")
results = load_results(job_info)
```

Uses `artifact_store.JobInfo` directly (same as the simulator) to keep the ecosystem consistent.

## Changes

### 1. Modify: [engine.py](impact_engine_measure/engine.py)

**Change return type** from `str` to `JobInfo`. Already available internally via `storage_manager.get_job()` ([artifact_store_adapter.py:44](impact_engine_measure/storage/artifact_store_adapter.py#L44)).

- Add `from artifact_store import JobInfo` to imports
- Change return type annotation: `-> str` becomes `-> JobInfo`
- Change final line from `return fit_output.results_path` to `return storage_manager.get_job()`
- Update docstring

### 2. New file: `impact_engine_measure/results.py`

**`MeasureJobResult` dataclass** — typed container for all job artifacts:

| Field | Type | Source |
|---|---|---|
| `job_id` | `str` | `job_info.job_id` |
| `schema_version` | `str` | `manifest.json` |
| `model_type` | `str` | `manifest.json` |
| `created_at` | `str` | `manifest.json` |
| `config` | `Dict[str, Any]` | `config.yaml` |
| `impact_results` | `Dict[str, Any]` | `impact_results.json` |
| `products` | `pd.DataFrame` | `products.parquet` |
| `business_metrics` | `pd.DataFrame` | `business_metrics.parquet` |
| `transformed_metrics` | `pd.DataFrame` | `transformed_metrics.parquet` |
| `model_artifacts` | `Dict[str, pd.DataFrame]` | `{model_type}__{name}.parquet` (prefix stripped) |

**`load_results(job_info: JobInfo) -> MeasureJobResult`** — manifest-driven loader:

1. `store = job_info.get_store()` — get `ArtifactStore` for the job directory
2. Validate directory and `manifest.json` exist (`FileNotFoundError`)
3. Load manifest, validate major schema version matches `SCHEMA_VERSION` from [models/base.py:9](impact_engine_measure/models/base.py#L9)
4. Load each file using format-appropriate reader (`read_parquet`, `read_json`, `read_yaml`)
5. Collect model-specific artifacts (keys not in fixed pipeline set) into `model_artifacts` with `{model_type}__` prefix stripped
6. Return `MeasureJobResult`

Private helpers: `_validate_manifest_version(manifest)`, `_load_file(store, file_info)`

### 3. Modify: [\_\_init\_\_.py](impact_engine_measure/__init__.py)

Add exports: `load_results`, `MeasureJobResult` (imported from `.results`). Add both to `__all__`.

### 4. New file: `tests/test_load_results.py`

- **Round-trip test** — `evaluate_impact` → `load_results`, verify all fields
- **Synthetic manifest tests** (fast, no pipeline run) — write artifacts + manifest to temp dir, verify manifest-driven loading and prefix stripping
- **Error tests** — missing job dir, missing manifest, incompatible schema version

### 5. Simplification sweep

With `evaluate_impact` returning `JobInfo` and `load_results` available, simplify all places that manually parse paths or load JSON:

**Tests:**
- [tests/test_evaluate_impact.py](tests/test_evaluate_impact.py) — 4 tests: replace `result_path` string handling + `open()`/`json.load()` (lines 69-70, 244-245) with `JobInfo` attribute access and `store.read_json()`
- [tests/models/metrics_approximation/test_pipeline.py](tests/models/metrics_approximation/test_pipeline.py) — line 83: same `open()`/`json.load()` pattern

**Demo notebooks:**
- [docs/source/models/demo_experiment.ipynb](docs/source/models/demo_experiment.ipynb) — cell 10: replace manual JSON loading with `load_results(job_info)`, then access `result.impact_results`

**Documentation:**
- [docs/source/usage.md](docs/source/usage.md) — lines 37-68: update examples to show `JobInfo` return type and `load_results()` usage instead of manual path/JSON handling

### 6. Modify: [BACKLOG.md](BACKLOG.md)

Move `load_results(job_id)` from **Open** to **Done**.

## Verification

```bash
hatch run lint
hatch run test
```
