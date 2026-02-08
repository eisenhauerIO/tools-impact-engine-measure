# Plan B: Add `get_fit_params()` to ModelInterface

## Context

`ModelsManager.fit_model()` passes the entire flat `MEASUREMENT.PARAMS` dict as `**kwargs` to every adapter's `fit()`. This includes params belonging to other models (e.g., experiment adapter receives `intervention_date`, `order`, `n_strata`). The experiment adapter forwards these to `statsmodels.fit(**kwargs)`, which crashes on unknown keys. Other adapters silently ignore irrelevant keys, but the pollution is a latent bug everywhere.

**Fix**: Each adapter declares which params it accepts via a new `get_fit_params()` method. The manager filters before calling `fit()`.

## Design

Add `get_fit_params(self, params: Dict) -> Dict` to `ModelInterface`:
- Default returns all params unchanged (backward compatible for custom adapters)
- Each built-in adapter overrides to filter
- Manager calls it between `validate_params()` and `fit()`

Key ordering: **validate full params -> filter -> fit filtered**. Validation still sees all params so it can check for required config keys.

## Changes

### 1. `science/impact_engine/models/base.py` -- add method

Insert after `validate_params()` (after line 138):

```python
def get_fit_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """Filter parameters to only those accepted by this adapter's fit().

    Called by ModelsManager before fit() to prevent cross-model param pollution.
    Default returns all params (backward compatible). Built-in adapters override.

    Args:
        params: Full params dict (config PARAMS merged with caller overrides).

    Returns:
        Filtered dict for fit().
    """
    return dict(params)
```

### 2. `science/impact_engine/models/manager.py` -- call it

Change lines 72-76. Before:

```python
result: ModelResult = self.model.fit(
    data=data,
    **params,
)
```

After:

```python
fit_params = self.model.get_fit_params(params)

result: ModelResult = self.model.fit(
    data=data,
    **fit_params,
)
```

### 3. `science/impact_engine/models/interrupted_time_series/adapter.py` -- allowlist

Add after `validate_params()` (after line 104):

```python
_FIT_PARAMS = frozenset({
    "intervention_date",
    "dependent_variable",
    "order",
    "seasonal_order",
})

def get_fit_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """ITS accepts intervention_date, dependent_variable, order, seasonal_order."""
    return {k: v for k, v in params.items() if k in self._FIT_PARAMS}
```

Matches exactly what `fit()` extracts: `intervention_date` (line 127), `dependent_variable` (line 128), `order`/`seasonal_order` (lines 273-274 in `_prepare_model_input`).

### 4. `science/impact_engine/models/subclassification/adapter.py` -- allowlist

Add after `validate_params()` (after line 99):

```python
_FIT_PARAMS = frozenset({"dependent_variable"})

def get_fit_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """Subclassification only uses dependent_variable from fit kwargs."""
    return {k: v for k, v in params.items() if k in self._FIT_PARAMS}
```

Only `dependent_variable` is read from kwargs (line 119). All other params (treatment_column, covariate_columns, n_strata, estimand) already in `self.config` from `connect()`.

### 5. `science/impact_engine/models/metrics_approximation/adapter.py` -- empty

Add after `validate_params()` (after line 114):

```python
def get_fit_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """Metrics approximation has no fit-time params from config.

    All configuration (column names, response function, response params)
    is stored in self.config during connect().
    """
    return {}
```

Also fixes latent bug where `fit()` line 152 merges ALL kwargs into response function params: `response_params = {**self.config["response_params"], **kwargs}`.

### 6. `science/impact_engine/models/experiment/adapter.py` -- denylist + review fixes

**get_fit_params** -- denylist approach (because experiment's legitimate kwargs are open-ended statsmodels params like `cov_type`, `cov_kwds`, `use_t`):

```python
_CONFIG_PARAMS = frozenset({
    "dependent_variable", "intervention_date", "order", "seasonal_order",
    "n_strata", "estimand", "treatment_column", "covariate_columns",
    "formula", "metric_before_column", "metric_after_column",
    "baseline_column", "RESPONSE",
})

def get_fit_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """Exclude known config keys, pass library kwargs through to statsmodels."""
    return {k: v for k, v in params.items() if k not in self._CONFIG_PARAMS}
```

**Additional review fixes** (from code/design review):

- `connect()`: store only `{"formula": formula}` instead of full config dict (match other adapters)
- `validate_params()`: add `isinstance(formula, str)` check to match `connect()`
- `fit()`: add `validate_data()` call before fitting (match other adapters' pattern)

### 7. Test changes

**`science/impact_engine/tests/test_models_manager.py`**:
- Existing tests using `Mock(spec=ModelInterface)` need `mock_model.get_fit_params.side_effect = lambda p: p` to preserve pass-through behavior (since Mock auto-creates the new method but returns a Mock object by default)
- Add `TestModelsManagerParamFiltering` class:
  - `test_fit_model_filters_params_via_get_fit_params` -- verify manager calls get_fit_params and fit receives filtered result
  - `test_validate_params_receives_full_params` -- verify validation sees all params before filtering
  - `test_overrides_subject_to_filtering` -- verify caller overrides are also filtered

**Each adapter's test file** -- add `TestXxxGetFitParams` class:

- **ITS** (`interrupted_time_series/tests/test_adapter.py`): verify only 4 keys pass through, others excluded
- **Subclassification** (`subclassification/tests/test_adapter.py`): verify only `dependent_variable` passes through
- **Metrics** (`metrics_approximation/tests/test_adapter.py`): verify empty dict returned
- **Experiment** (`experiment/tests/test_adapter.py`): verify config keys excluded, library kwargs (`cov_type`, `use_t`) pass through

## Verification

1. `hatch run pytest science/impact_engine/models/experiment/tests/` -- experiment tests pass
2. `hatch run test` -- full suite passes
3. `hatch run lint` -- clean
4. Commit to `refactor-get-fit-params` branch, push, create PR, verify CI green
