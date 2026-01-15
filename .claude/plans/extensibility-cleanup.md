# Architecture Cleanup Plan: Impact Engine Extensibility

## Goal
Get shared capabilities into pristine shape so impact measurement models and data sources can be developed in parallel without interference.

## Current Issues Summary

| Priority | Issue | Location | Impact |
|----------|-------|----------|--------|
| HIGH | Storage coupling | `models/manager.py:83` sets `model.storage` directly | Models have inconsistent result handling |
| HIGH | Simulator coupling | `metrics/adapter_catalog_simulator.py` | Hard imports prevent testing/swapping |
| MEDIUM | Transform schema coupling | `transforms/library.py:159,162,233` | Hardcoded `"catalog_simulator"` source |
| MEDIUM | Config param injection | `config.py` injects `enrichment_start` | Hidden dependencies |
| LOW | Inconsistent registries | 3 different patterns | Harder to extend |

---

## Phase 1: Storage Abstraction (HIGH PRIORITY)

### 1.1 Add ModelResult to base.py
**File**: `science/impact_engine/models/base.py`

```python
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

@dataclass
class ModelResult:
    """Standardized model result container."""
    model_type: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"model_type": self.model_type, **self.data, "metadata": self.metadata}

@runtime_checkable
class StorageBackend(Protocol):
    """Protocol for storage backends."""
    def write_json(self, path: str, data: Dict[str, Any]) -> None: ...
    def full_path(self, path: str) -> str: ...
```

Update `fit()` return type annotation to `ModelResult`.

### 1.2 Move storage handling to ModelsManager
**File**: `science/impact_engine/models/manager.py`

```python
def fit_model(self, data, output_path=".", storage=None, **kwargs) -> str:
    # ... validation ...
    result: ModelResult = self.model.fit(data=data, **fit_params)

    # Centralized storage handling
    if storage:
        result_path = f"{output_path}/impact_results.json"
        storage.write_json(result_path, result.to_dict())
        return storage.full_path(result_path)
    return f"memory://{result.model_type}"
```

Remove line 83 (`self.model.storage = storage`).

### 1.3 Update InterruptedTimeSeriesAdapter
**File**: `science/impact_engine/models/interrupted_time_series/adapter.py`

- Remove `self.storage` usage
- Return `ModelResult(model_type="interrupted_time_series", data=standardized_results, metadata={...})`

### 1.4 Update MetricsApproximationAdapter
**File**: `science/impact_engine/models/metrics_approximation/adapter.py`

- Wrap existing dict return in `ModelResult`

---

## Phase 2: Transform Colocation (MEDIUM PRIORITY)

**Approach**: Accept that transforms are source/model-specific. Colocate them with their adapters.

### 2.1 Move registry to core
**File**: `science/impact_engine/core/transforms.py` (NEW)

Move registry infrastructure from `transforms/registry.py`:
- `TRANSFORM_REGISTRY` dict
- `register_transform()` decorator
- `get_transform()` lookup
- `apply_transform()` executor
- `passthrough` transform (generic utility)

### 2.2 Create catalog_simulator transforms
**File**: `science/impact_engine/metrics/catalog_simulator/transforms.py` (NEW)

Move from `transforms/library.py`:
- `prepare_simulator_for_approximation` (keeps its hardcoded schema - that's correct)
- `_detect_id_column` helper

### 2.3 Create ITS transforms
**File**: `science/impact_engine/models/interrupted_time_series/transforms.py` (NEW)

Move from `transforms/library.py`:
- `aggregate_by_date`

### 2.4 Create metrics_approximation transforms
**File**: `science/impact_engine/models/metrics_approximation/transforms.py` (NEW)

Move from `transforms/library.py`:
- `aggregate_for_approximation`

### 2.5 Reorganize catalog_simulator adapter
**File**: `science/impact_engine/metrics/catalog_simulator/adapter.py` (NEW)

Rename `metrics/adapter_catalog_simulator.py` → `metrics/catalog_simulator/adapter.py`

### 2.6 Delete transforms directory
Remove `science/impact_engine/transforms/` entirely.

### 2.7 Update imports
Update `engine.py` and other files to import from new locations.

---

## Phase 3: Metrics Adapter Decoupling (HIGH PRIORITY)

### 3.1 Create simulator protocol
**File**: `science/impact_engine/metrics/protocols.py` (NEW)

```python
@runtime_checkable
class MetricsSimulator(Protocol):
    def simulate_metrics(self, job, config_path: str) -> None: ...
    def simulate_product_details(self, job, config_path: str): ...
    def enrich(self, config_path: str, job): ...
```

### 3.2 Create simulator factory
**File**: `science/impact_engine/metrics/simulator_factory.py` (NEW)

Lazy import wrapper that returns protocol-compliant backend.

### 3.3 Update CatalogSimulatorAdapter
**File**: `science/impact_engine/metrics/adapter_catalog_simulator.py`

- Accept optional `simulator_backend` in `__init__` for DI
- Use lazy-loading property for default backend
- Replace direct imports with factory calls

---

## Phase 4: Registry Unification (LOW PRIORITY)

### 4.1 Create unified registry base
**File**: `science/impact_engine/core/registry.py` (NEW)

```python
class Registry(Generic[T]):
    """Generic registry for components."""
    def register(self, name: str, cls: Type[T]) -> None: ...
    def get(self, name: str) -> T: ...

class FunctionRegistry:
    """Registry for functions (transforms, response functions)."""
    def register(self, name: str) -> Callable: ...  # decorator
    def get(self, name: str) -> Callable: ...
```

### 4.2 Migrate existing registries
- `models/factory.py` -> use `Registry[Model]`
- `metrics/factory.py` -> use `Registry[MetricsInterface]`
- `transforms/registry.py` -> use `FunctionRegistry`

Keep backwards-compatible aliases (`MODEL_ADAPTERS`, `register_model_adapter`, etc.).

---

## Implementation Order

```
Phase 1.1 -> 1.2 -> 1.3 -> 1.4  (Storage - foundation)
    |
Phase 3.1 -> 3.2 -> 3.3  (Metrics - independent of Phase 1)
    |
Phase 2.1 -> 2.2 -> 2.3 -> 2.4  (Transforms - uses new patterns)
    |
Phase 4.1 -> 4.2  (Registry - cleanup, lowest priority)
```

**Phases 1 and 3 can run in parallel** (no dependencies).

---

## Files to Modify

| Phase | File | Action |
|-------|------|--------|
| 1 | `models/base.py` | Add `ModelResult`, `StorageBackend` |
| 1 | `models/manager.py` | Centralize storage, remove line 83 |
| 1 | `models/interrupted_time_series/adapter.py` | Return `ModelResult` |
| 1 | `models/metrics_approximation/adapter.py` | Return `ModelResult` |
| 2 | `core/transforms.py` | NEW - registry + passthrough |
| 2 | `metrics/catalog_simulator/transforms.py` | NEW - source-specific transforms |
| 2 | `metrics/catalog_simulator/adapter.py` | MOVE from `adapter_catalog_simulator.py` |
| 2 | `models/interrupted_time_series/transforms.py` | NEW - `aggregate_by_date` |
| 2 | `models/metrics_approximation/transforms.py` | NEW - `aggregate_for_approximation` |
| 2 | `transforms/` | DELETE entire directory |
| 2 | `engine.py` | Update imports |
| 3 | `metrics/protocols.py` | NEW - `MetricsSimulator` protocol |
| 3 | `metrics/simulator_factory.py` | NEW - lazy loading |
| 3 | `metrics/catalog_simulator/adapter.py` | Use DI pattern |
| 4 | `core/registry.py` | NEW - unified base |
| 4 | `models/factory.py` | Use unified registry |
| 4 | `metrics/factory.py` | Use unified registry |

---

## Verification

### Unit Tests
```bash
# After Phase 1
pytest science/impact_engine/models/tests/ -v

# After Phase 2 (transforms now colocated)
pytest science/impact_engine/models/tests/ -v
pytest science/impact_engine/metrics/tests/ -v

# After Phase 3
pytest science/impact_engine/metrics/tests/ -v
```

### Integration Tests
```bash
# Full pipeline test
pytest science/integration_tests/ -v
```

### Manual Verification
```bash
# Run demo workflows
python science/demo/workflow_metrics_approximation.py
python science/demo/workflow_enrichment.py
```

---

## Outcome

After completion:
- **Models** can be developed independently (return `ModelResult`, no storage knowledge)
- **Data sources** can be swapped/mocked (protocol + factory pattern)
- **Transforms** colocated with their adapters (clear ownership, source-specific is OK)
- **Registries** follow consistent pattern (easy to add new components)
