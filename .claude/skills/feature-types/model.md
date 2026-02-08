# Feature Type: Measurement Model

Instructions for scaffolding a new measurement model adapter in the impact-engine-measure project. The project uses an adapter-based plugin architecture where each model is a self-contained subpackage under `science/impact_engine/models/`.

Adapters must be thin wrappers around the underlying library — keep custom logic minimal.

## Naming

Derive these values from `FEATURE_NAME`:

- `MODEL_NAME`: The snake_case name (e.g., `difference_in_differences`)
- `CLASS_NAME`: PascalCase + "Adapter" suffix (e.g., `DifferenceInDifferencesAdapter`)
- `MODEL_DIR`: `science/impact_engine/models/{MODEL_NAME}`
- `REGISTRY_KEY`: Same as `MODEL_NAME` (used in `@MODEL_REGISTRY.register_decorator("MODEL_NAME")`)

## Requirements

Ask the user these 8 questions:

1. **Statistical method**: What statistical/ML method does this model implement? (e.g., difference-in-differences, synthetic control, Bayesian structural time series, propensity score matching)
2. **Python library**: What library implements this method? (e.g., statsmodels, causalimpact, scikit-learn, or custom implementation)
3. **Required parameters**: What configuration parameters does the model need in `connect()`? List each with type and default. These go in `MEASUREMENT.PARAMS` in config.
4. **Required data columns**: What columns must be present in the input DataFrame for `fit()`? (e.g., date, dependent variable, treatment indicator, group indicator)
5. **Fit-time parameters**: What parameters does `fit()` need via `**kwargs`? (e.g., intervention_date, dependent_variable, treatment_column)
6. **Output structure**: What should `impact_estimates` contain in the `ModelResult.data` dict? (e.g., treatment_effect, standard_error, p_value, confidence_interval)
7. **Model summary fields**: What model diagnostics should go in `model_summary`? (e.g., n_observations, r_squared, aic, bic)
8. **Transform needs**: Does the model need a custom data transform in `transforms.py`? (e.g., aggregation, pivoting, differencing)

## References

Read these files before writing any code to match exact code style and patterns:

```
science/impact_engine/models/base.py
science/impact_engine/models/factory.py
science/impact_engine/models/conftest.py
science/impact_engine/models/interrupted_time_series/adapter.py
science/impact_engine/models/interrupted_time_series/__init__.py
science/impact_engine/models/interrupted_time_series/transforms.py
science/impact_engine/models/interrupted_time_series/tests/test_adapter.py
science/impact_engine/models/metrics_approximation/adapter.py
science/impact_engine/config_defaults.yaml
```

## Plan

The implementation plan should include:

1. **Adapter design** — summarize what the adapter's `connect()`, `fit()`, and `validate_data()` methods will do, including which library calls they delegate to.
2. **Data flow** — describe the path from raw input DataFrame through any transforms to the library's API and back to `ModelResult`.
3. **Transform details** — if a custom transform is needed, describe what it does.

## Implementation

### Create directory structure

```
science/impact_engine/models/{MODEL_NAME}/
science/impact_engine/models/{MODEL_NAME}/tests/
```

### Create `adapter.py`

Create `science/impact_engine/models/{MODEL_NAME}/adapter.py`.

#### File structure (in this order):
1. Module docstring describing the model
2. Imports: `logging`, standard lib, third-party libs, then relative imports from `..base` and `..factory`
3. Optional: `@dataclass` container for transformed input (like `TransformedInput` in ITS adapter)
4. The adapter class with `@MODEL_REGISTRY.register_decorator("{MODEL_NAME}")`

#### Class requirements:
```python
@MODEL_REGISTRY.register_decorator("{MODEL_NAME}")
class {CLASS_NAME}(ModelInterface):
    """One-line description.

    Constraints:
    - List data requirements
    - List parameter requirements
    """

    def __init__(self):
        """Initialize the {CLASS_NAME}."""
        self.logger = logging.getLogger(__name__)
        self.is_connected = False
        self.config = None

    def connect(self, config: Dict[str, Any]) -> bool:
        """Initialize model with configuration parameters.

        Config is pre-validated with defaults merged via process_config().
        """
        # Validate and store config parameters
        # Convert YAML list types to tuples if needed
        # Set self.config, self.is_connected = True
        # Return True

    def validate_connection(self) -> bool:
        """Validate that the model is properly initialized and ready to use."""
        # Check self.is_connected
        # Optionally verify library availability via import

    def validate_params(self, params: Dict[str, Any]) -> None:
        """Validate {MODEL_NAME}-specific parameters.

        Raises:
            ValueError: If required parameters are missing.
        """
        # Validate required fit-time params
        # Raise ValueError with helpful message referencing MEASUREMENT.PARAMS

    def fit(self, data: pd.DataFrame, **kwargs) -> ModelResult:
        """Fit the model and return results.

        Returns:
            ModelResult: Standardized result container.

        Raises:
            ValueError: If data validation fails.
            RuntimeError: If model fitting fails.
        """
        # 1. Extract kwargs (intervention_date, dependent_variable, storage, etc.)
        # 2. Check self.is_connected -> raise ConnectionError if not
        # 3. Validate data via self.validate_data()
        # 4. Prepare/transform input data
        # 5. Fit the model (wrap in try/except)
        # 6. Format results into standardized dict
        # 7. Return ModelResult(model_type="{MODEL_NAME}", data=results_dict)
        #
        # Error handling pattern:
        #   except Exception as e:
        #       self.logger.error(f"Error fitting {CLASS_NAME}: {e}")
        #       raise RuntimeError(f"Model fitting failed: {e}") from e

    def validate_data(self, data: pd.DataFrame) -> bool:
        """Validate input data meets model requirements."""
        # Check empty, check required columns, log warnings for failures

    def get_required_columns(self) -> List[str]:
        """Get required column names."""
        # Return list of required column names
```

#### Style rules (match existing code exactly):
- Line length: 100 chars (ruff configured)
- Type hints on all public method signatures
- Google-style docstrings with Args/Returns/Raises sections
- Use `self.logger` (not print) for all output
- All numeric values in results must be cast to `float()` or `int()` for JSON serialization
- Error messages must reference the config path (e.g., "Specify in MEASUREMENT.PARAMS configuration")

### Create `__init__.py`

Create `science/impact_engine/models/{MODEL_NAME}/__init__.py`:

```python
"""{Human-readable model name} for {brief purpose}.

This subpackage provides an implementation of {method name}
{brief description of what it does}.
"""

from .adapter import {CLASS_NAME}

__all__ = [
    "{CLASS_NAME}",
]
```

If `transforms.py` is created, also export the transform function(s).

### Create `transforms.py` (only if needed)

Only create this if the user indicated custom transforms are needed. Follow the pattern from `science/impact_engine/models/interrupted_time_series/transforms.py`.

### Create `tests/__init__.py`

Create `science/impact_engine/models/{MODEL_NAME}/tests/__init__.py`:
```python
"""Tests for {model name in human-readable form} model."""
```

### Create `tests/test_adapter.py`

Create `science/impact_engine/models/{MODEL_NAME}/tests/test_adapter.py`.

#### Required test classes:

```python
"""Tests for {CLASS_NAME}."""

import pandas as pd
import pytest

from impact_engine.models.conftest import merge_model_params
from impact_engine.models.{MODEL_NAME} import {CLASS_NAME}


class Test{CLASS_NAME}Connect:
    """Tests for connect() method."""

    def test_connect_success(self): ...
    def test_connect_invalid_{param}(self): ...

class Test{CLASS_NAME}ValidateParams:
    """Tests for validate_params() method."""

    def test_validate_params_valid(self): ...
    def test_validate_params_missing_required(self): ...

class Test{CLASS_NAME}Fit:
    """Tests for fit() method."""

    def test_fit_not_connected(self): ...
    def test_fit_returns_model_result(self): ...
    def test_fit_result_data_structure(self): ...
    def test_fit_impact_estimates_structure(self): ...
    def test_fit_model_summary_structure(self): ...

class Test{CLASS_NAME}ValidateData:
    """Tests for validate_data() method."""

    def test_valid_data(self): ...
    def test_empty_dataframe(self): ...
    def test_missing_columns(self): ...

class Test{CLASS_NAME}GetRequiredColumns:
    """Tests for get_required_columns() method."""

    def test_required_columns(self): ...
```

#### Test patterns:
- **No mocking the underlying library.** Fit tests must be real end-to-end: create synthetic data, call the actual library, and verify results. This is the primary value of adapter tests — proving the integration works.
- Use `merge_model_params()` from `impact_engine.models.conftest` for configs needing defaults
- Use `pytest.raises(ExceptionType, match="pattern")` for error tests
- Create test data inline as `pd.DataFrame` (no external fixture files)
- Assert `isinstance(result, ModelResult)` and `result.model_type == "{MODEL_NAME}"`

### Update `factory.py`

Edit `science/impact_engine/models/factory.py` to add the import trigger at the bottom, maintaining alphabetical order:

```python
from .interrupted_time_series import InterruptedTimeSeriesAdapter  # noqa: E402, F401
from .metrics_approximation import MetricsApproximationAdapter  # noqa: E402, F401
from .{MODEL_NAME} import {CLASS_NAME}  # noqa: E402, F401
```

The `# noqa: E402, F401` comment is required to suppress ruff warnings.

### Update `ExperimentAdapter` denylist

The `ExperimentAdapter` uses a denylist (`_CONFIG_PARAMS`) to exclude known config keys from other models. When adding new config params, you **must** add them to `science/impact_engine/models/experiment/adapter.py` `_CONFIG_PARAMS` frozenset. Otherwise, the new params will leak through to `statsmodels.OLS.fit()` as unrecognized kwargs.

### Update `config_defaults.yaml` (if needed)

If the model has default configuration parameters, add them under `MEASUREMENT.PARAMS` in `science/impact_engine/config_defaults.yaml`. Group with a comment:

```yaml
    # {Human-readable model name} params
    {new_param}: {default_value}
```

Use `null` for REQUIRED parameters. Use actual values for optional parameters with defaults.

## Verification

Before declaring done, verify:

- [ ] Work is on a feature branch (not `main`)
- [ ] `adapter.py` has `@MODEL_REGISTRY.register_decorator("{MODEL_NAME}")` decorator
- [ ] `adapter.py` class extends `ModelInterface` and implements `connect`, `fit`, `validate_params`
- [ ] `adapter.py` returns `ModelResult(model_type="{MODEL_NAME}", data=...)` from `fit()`
- [ ] `adapter.py` uses `self.logger = logging.getLogger(__name__)` in `__init__`
- [ ] `adapter.py` has proper error handling: `ConnectionError`, `ValueError`, `RuntimeError`
- [ ] `__init__.py` exports the adapter class in `__all__`
- [ ] `factory.py` has the import trigger at the bottom with `# noqa: E402, F401`
- [ ] `tests/test_adapter.py` covers connect, validate_params, fit, validate_data, get_required_columns
- [ ] `tests/test_adapter.py` uses `merge_model_params()` for configs needing defaults
- [ ] All local tests pass
- [ ] Lint passes
- [ ] `config_defaults.yaml` updated if the model has default parameters
- [ ] PR created targeting `main`
- [ ] CI is green
