# Codebase Simplification Analysis

## Overview

This document identifies simplification opportunities in the impact-engine codebase, dead code to remove, and the conditions that would need to be true to enable each simplification.

---

## 1. Dead Code to Remove (No Conditions Required) - DONE

These items are definitively unused and can be safely removed:

### 1.1 Unused Config Functions - DONE
**File:** [config.py](science/impact_engine/config.py)

| Function | Line | Status |
|----------|------|--------|
| `get_measurement_config()` | ~78 | DELETED |
| `get_measurement_params()` | ~82 | DELETED |

### 1.2 Unused ColumnContract Class - DONE
**File:** [core/contracts.py](science/impact_engine/core/contracts.py)

The `ColumnContract` class and its methods (`find_in_df()`, `validate_presence()`) were deleted. Updated `__all__` in [core/__init__.py](science/impact_engine/core/__init__.py).

### 1.3 Unused Factory Function (Test-Only) - DONE
**File:** [metrics/factory.py](science/impact_engine/metrics/factory.py)

`create_metrics_manager_from_config()` was deleted. Updated exports in [metrics/__init__.py](science/impact_engine/metrics/__init__.py). Removed 2 tests that specifically tested this function.

---

## 2. Simplification Opportunities with Conditions

### 2.1 Redundant Factory Functions - DONE

**File:** [metrics/factory.py](science/impact_engine/metrics/factory.py)

Consolidated to single `create_metrics_manager(config)` that takes a parsed config dict.
- Updated engine.py to use `create_metrics_manager(config, parent_job=job)`
- Updated workflow_enrichment.py to use `parse_config_file()` then `create_metrics_manager()`
- Updated test_metrics_manager.py
- Updated metrics/__init__.py exports

### 2.2 Thin Config Accessor Functions - DONE

**File:** [config.py](science/impact_engine/config.py)

Removed `get_source_config()`, `get_source_type()`, `get_transform_config()`.
- engine.py now uses direct dict access: `config["DATA"]["SOURCE"]["CONFIG"]`
- Enrichment injection moved to process_config() (see 2.10)

### 2.3 Duplicate Aggregation Logic - SKIPPED (per user request)

**Files:**
- [metrics/interrupted_time_series/transforms.py](science/impact_engine/metrics/interrupted_time_series/transforms.py) - `aggregate_by_date()`
- [models/metrics_approximation/transforms.py](science/impact_engine/models/metrics_approximation/transforms.py) - `aggregate_for_approximation()`

### 2.4 Backwards Compatibility for Config Key Case - DONE

**File:** [metrics/file/adapter.py](science/impact_engine/metrics/file/adapter.py)

Removed uppercase key fallbacks. Now uses lowercase only: `path`, `date_column`, `product_id_column`.

### 2.5 Redundant Python Default Fallbacks - DONE

**File:** [core/config_bridge.py](science/impact_engine/core/config_bridge.py)

Removed Python dictionary fallback from `_get_catalog_simulator_defaults()`. Now directly returns `defaults["CATALOG_SIMULATOR"]` from YAML, making config_defaults.yaml the single source of truth.

### 2.6 Legacy Column Handling in Adapters - DONE

**File:** [metrics/catalog_simulator/adapter.py](science/impact_engine/metrics/catalog_simulator/adapter.py)

Removed legacy 'quantity' column fallback handling. Contract (MetricsSchema) now handles column mapping; violations fail explicitly.

### 2.7 Validation Duplication Across Layers - DONE

**File:** [metrics/catalog_simulator/adapter.py](science/impact_engine/metrics/catalog_simulator/adapter.py)

Removed redundant mode/seed validation in `connect()`. Config is pre-validated by process_config(); adapter trusts validated input.

### 2.8 Model-Specific Validation Branching - DONE

**File:** [core/validation.py](science/impact_engine/core/validation.py)

Removed `_validate_its_params()` function and the model-specific if/elif validation chain from `validate_parameters()`. Models validate via their own `validate_params()` method.

### 2.9 Metadata Duplication in Adapters - DONE

**Files:**
- [metrics/catalog_simulator/adapter.py](science/impact_engine/metrics/catalog_simulator/adapter.py)
- [metrics/file/adapter.py](science/impact_engine/metrics/file/adapter.py)
- [metrics/manager.py](science/impact_engine/metrics/manager.py)

Removed `metrics_source` and `retrieval_timestamp` additions from both adapters. Metadata now added once in `MetricsManager.retrieve_metrics()` using the `source_type` parameter passed from factory.

### 2.10 Implicit Enrichment Config Threading - DONE

**File:** [core/validation.py](science/impact_engine/core/validation.py)

Moved enrichment_start injection to `process_config()` (Stage 6, lines 367-375).
Removed `get_transform_config()` from config.py.

---

## 3. Architectural Simplifications (Larger Refactors)

### 3.1 Excessive Base Class Default Methods

**File:** [models/base.py](science/impact_engine/models/base.py)

Model base class has many methods with trivial default implementations:
- `validate_connection()` - returns True
- `validate_data()` - checks if not empty
- `transform_outbound()`/`transform_inbound()` - pass-through

**Condition:** If subclasses always override these, make them abstract. If never overridden, move to manager.

### 3.2 Export Cleanup for Internal Functions - DONE

**File:** [core/validation.py](science/impact_engine/core/validation.py)

Prefixed internal validation functions with `_` to mark as private:
- `validate_file()` → `_validate_file()`
- `validate_format()` → `_validate_format()`
- `validate_structure()` → `_validate_structure()`
- `validate_parameters()` → `_validate_parameters()`

These are implementation details of `process_config()` and not part of the public API.

---

## 4. Summary: Priority Actions

### Immediate (No conditions, safe to remove):
1. ~~Delete `get_measurement_config()` and `get_measurement_params()` from config.py~~ DONE
2. ~~Delete unused `ColumnContract` class from contracts.py~~ DONE
3. Remove internal validation functions from public exports

### Short-term (Verify conditions first):
4. ~~Consolidate 2 remaining factory functions to 1 in metrics/factory.py~~ DONE
5. ~~Create generic aggregate function to deduplicate transform logic~~ SKIPPED
6. ~~Remove case-sensitivity backwards compatibility in file adapter~~ DONE

### Medium-term (Requires migration):
7. Remove legacy 'quantity' column handling (2.6)
8. Move model-specific validation into model classes (2.8)
9. Centralize metadata addition in MetricsManager (2.9)

---

## 5. Verification

After each simplification:
1. Run `pytest science/impact_engine/tests/` for unit tests
2. Run `pytest science/integration_tests/` for integration tests
3. Execute demo workflow: `python science/demo/workflow.py`

---

## 6. Next Steps (Resume Here)

**Completed in previous session:**
- 2.1: Consolidated factory functions ✓
- 2.2: Removed thin config accessor functions ✓
- 2.4: Removed uppercase key backwards compatibility ✓
- 2.10: Moved enrichment injection to process_config ✓

**Completed in current session:**
- 2.5: Removed Python default fallbacks in config_bridge.py ✓
- 2.6: Removed legacy 'quantity' column handling in catalog_simulator/adapter.py ✓
- 2.7: Removed redundant mode/seed validation in catalog_simulator/adapter.py connect() ✓
- 2.8: Removed _validate_its_params() from validation.py ✓
- 2.9: Centralized metadata addition in MetricsManager.retrieve_metrics() ✓

**All section 2 simplifications complete.** Remaining items in sections 3-4 are larger architectural refactors.

**Run tests to verify changes:**
```bash
pytest science/impact_engine/tests/ -v
```
