# Feature Type: Demo Notebook

Instructions for creating a demo notebook for a measurement model in the impact-engine-measure project. Demo notebooks are runnable documentation that exercise `evaluate_impact()` end-to-end with simulated data.

All demo notebooks use the online retail simulator for data generation.

## Naming

Derive these values from `MODEL_NAME`:

- `NOTEBOOK_FILE`: `documentation/notebooks/demo_{MODEL_NAME}.ipynb`
- `CATALOG_CONFIG`: `documentation/notebooks/configs/demo_{MODEL_NAME}_catalog.yaml`
- `OUTPUT_DIR`: `output/demo_{MODEL_NAME}` (relative to notebooks directory)

## Requirements

Ask the user these questions:

1. **Data type**: Does the model need time-series data (multiple dates) or cross-sectional data (single day)? Cross-sectional: set `start_date = end_date`. Time-series: set a date range.
2. **Transform**: Does the model need a custom transform, or is passthrough (no TRANSFORM config) sufficient?
3. **Enrichment**: Does the model need enrichment (treatment assignment)? If yes, what `enrichment_fraction` and `enrichment_start`?
4. **Model params**: What goes in `MEASUREMENT.PARAMS`? (e.g., treatment_column, covariate_columns, dependent_variable, intervention_date)
5. **Results structure**: What fields are in `impact_estimates` and `model_summary` in the results JSON?
6. **Artifacts**: What artifact files does the model produce? (e.g., `{MODEL_NAME}__artifact_name.parquet`)

## References

Read these files before writing any code to match exact style and patterns:

```
documentation/notebooks/demo_metrics_approximation.ipynb
documentation/notebooks/configs/demo_metrics_approximation_catalog.yaml
documentation/notebooks/demo_basic.ipynb
science/impact_engine/models/{MODEL_NAME}/adapter.py
```

## Implementation

### 1. Create catalog config

**File**: `documentation/notebooks/configs/demo_{MODEL_NAME}_catalog.yaml`

Standard catalog config (same for all demos unless model needs special products):

```yaml
STORAGE:
  PATH: output/demo_{MODEL_NAME}
RULE:
  PRODUCTS:
    FUNCTION: simulate_products_rule_based
    PARAMS:
      num_products: 100
      seed: 42
```

### 2. Create debug script (develop first, delete after)

**File**: `documentation/notebooks/demo_{MODEL_NAME}.py`

A plain Python script with the same logic as the eventual notebook. Allows running with `hatch run python documentation/notebooks/demo_{MODEL_NAME}.py` for easy debugging (breakpoints, stack traces). Run from the `documentation/notebooks/` directory.

Script structure:
1. Create output directory, run `simulate()`, save products CSV
2. Build config dict, write YAML
3. Call `evaluate_impact(config_path, results_path)`
4. Load and print results JSON
5. Load and print artifact parquet files

Once it works end-to-end, convert to notebook and delete the script.

### 3. Create notebook (convert from script)

**File**: `documentation/notebooks/demo_{MODEL_NAME}.ipynb`

Follow the `demo_metrics_approximation.ipynb` cell pattern:

| Cell | Type | Content |
|------|------|---------|
| 0 | md | Title + overview + workflow summary |
| 1 | md | "## Setup" |
| 2 | code | Imports |
| 3 | md | "## Step 1: Create Products Catalog" + note |
| 4 | code | `simulate()`, save CSV, print summary |
| 5 | md | "## Step 2: Configure {Model}" + config explanation |
| 6 | code | Build config dict, write YAML, print summary |
| 7 | md | "## Step 3: Run Impact Evaluation" + pipeline explanation |
| 8 | code | `evaluate_impact()`, print results path |
| 9 | md | "## Step 4: Review Results" |
| 10 | code | Load JSON, print formatted results |
| 11 | code | Load artifact parquet, print formatted table |

### Config dict pattern

```python
config = {
    "DATA": {
        "SOURCE": {
            "type": "simulator",
            "CONFIG": {
                "mode": "rule",
                "seed": 42,
                "start_date": "...",
                "end_date": "...",
                "path": str(products_path),
            },
        },
        # ENRICHMENT block (if needed)
        # TRANSFORM block (if needed, omit for passthrough)
    },
    "MEASUREMENT": {
        "MODEL": "{MODEL_NAME}",
        "PARAMS": { ... },
    },
}
```

## Verification

- [ ] Catalog config created at `configs/demo_{MODEL_NAME}_catalog.yaml`
- [ ] Notebook created at `demo_{MODEL_NAME}.ipynb`
- [ ] Debug script deleted
- [ ] Notebook cell structure matches the pattern (md/code alternating)
- [ ] `evaluate_impact()` produces results with non-trivial values
- [ ] Artifact files are loaded and displayed
- [ ] `hatch run test` passes (notebook doesn't break existing tests)
- [ ] `hatch run lint` passes
