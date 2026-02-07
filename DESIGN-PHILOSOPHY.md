# Design Philosophy

## Models: Thin Wrappers

Each measurement model adapter should be as thin a wrapper as possible around the underlying Python library. Minimize custom logic; delegate to the library for all statistical/ML work. The adapter's job is only to translate between the impact engine's interface (config, DataFrame in, ModelResult out) and the library's API.

## Model Output: File Formats

- **Main results**: JSON. Every model returns a `ModelResult`; the manager persists it via `storage.write_json("impact_results.json", result.to_dict())`. Models never write the main result file themselves.
- **Supplementary data artifacts**: Parquet. When a model needs to persist detailed row-level data (e.g., per-product impacts, per-stratum breakdowns), it writes parquet files directly via the storage backend inside `fit()`.
