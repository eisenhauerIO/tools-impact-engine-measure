---
name: add-measurement-model
description: Scaffold a new measurement model adapter following the project's adapter pattern, including adapter class, transforms, tests, and registry wiring. Use when creating a new model for the impact engine.
argument-hint: [model-name-in-snake-case]
allowed-tools: Read, Grep, Write, Edit, Bash, Glob
---

# Add Measurement Model

You are adding a new measurement model adapter to the impact-engine-measure project. The project uses an adapter-based plugin architecture where each model is a self-contained subpackage under `science/impact_engine/models/`.

Before starting, read `DESIGN-PHILOSOPHY.md` in the project root and follow its principles throughout. In particular, adapters must be thin wrappers around the underlying library — keep custom logic minimal.

## Step 0: Parse the argument

The user provides a model name in snake_case (e.g., `difference_in_differences`, `synthetic_control`). Store it as `MODEL_NAME`.

Derive these values:
- `MODEL_NAME`: The snake_case name (e.g., `difference_in_differences`)
- `CLASS_NAME`: PascalCase + "Adapter" suffix (e.g., `DifferenceInDifferencesAdapter`)
- `MODEL_DIR`: `science/impact_engine/models/{MODEL_NAME}`
- `REGISTRY_KEY`: Same as `MODEL_NAME` (used in `@MODEL_REGISTRY.register_decorator("MODEL_NAME")`)

## Step 1: Gather requirements from the user

Before writing any code, gather answers to the following questions. Use a **two-phase approach**:

**Phase A — Overview.** Print all 8 questions at once so the user can see the full scope of what you'll need:

1. **Statistical method**: What statistical/ML method does this model implement? (e.g., difference-in-differences, synthetic control, Bayesian structural time series, propensity score matching)
2. **Python library**: What library implements this method? (e.g., statsmodels, causalimpact, scikit-learn, or custom implementation)
3. **Required parameters**: What configuration parameters does the model need in `connect()`? List each with type and default. These go in `MEASUREMENT.PARAMS` in config.
4. **Required data columns**: What columns must be present in the input DataFrame for `fit()`? (e.g., date, dependent variable, treatment indicator, group indicator)
5. **Fit-time parameters**: What parameters does `fit()` need via `**kwargs`? (e.g., intervention_date, dependent_variable, treatment_column)
6. **Output structure**: What should `impact_estimates` contain in the `ModelResult.data` dict? (e.g., treatment_effect, standard_error, p_value, confidence_interval)
7. **Model summary fields**: What model diagnostics should go in `model_summary`? (e.g., n_observations, r_squared, aic, bic)
8. **Transform needs**: Does the model need a custom data transform in `transforms.py`? (e.g., aggregation, pivoting, differencing)

**Phase B — Walk through one by one.** After printing the overview, ask each question **individually** using AskUserQuestion (or plain text), waiting for the user's answer before moving to the next question. This keeps the conversation focused and avoids overwhelming the user.

## Step 2: Read reference files

Before writing any code, read these files to match exact code style and patterns:

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

## Step 3: Write a plan

Before writing any code, write out a concrete implementation plan and present it to the user for approval. The plan should include:

1. **Files to create/modify** — list every file path that will be created or edited.
2. **Adapter design** — summarize what the adapter's `connect()`, `fit()`, and `validate_data()` methods will do, including which library calls they delegate to.
3. **Data flow** — describe the path from raw input DataFrame through any transforms to the library's API and back to `ModelResult`.
4. **Key decisions** — note any non-obvious choices (e.g., how config params map to library kwargs, what gets cast to `float()`, error handling strategy).
5. **Transform details** — if a custom transform is needed, describe what it does.

Wait for the user to approve (or adjust) the plan before proceeding to code.

## Step 4: Create the directory structure

Create these directories:
```
science/impact_engine/models/{MODEL_NAME}/
science/impact_engine/models/{MODEL_NAME}/tests/
```

## Step 5: Create `adapter.py`

Create `science/impact_engine/models/{MODEL_NAME}/adapter.py`.

### File structure (in this order):
1. Module docstring describing the model
2. Imports: `logging`, standard lib, third-party libs, then relative imports from `..base` and `..factory`
3. Optional: `@dataclass` container for transformed input (like `TransformedInput` in ITS adapter)
4. The adapter class with `@MODEL_REGISTRY.register_decorator("{MODEL_NAME}")`

### Class requirements:
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

### Style rules (match existing code exactly):
- Line length: 100 chars (ruff configured)
- Type hints on all public method signatures
- Google-style docstrings with Args/Returns/Raises sections
- Use `self.logger` (not print) for all output
- All numeric values in results must be cast to `float()` or `int()` for JSON serialization
- Error messages must reference the config path (e.g., "Specify in MEASUREMENT.PARAMS configuration")

## Step 6: Create `__init__.py`

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

## Step 7: Create `transforms.py` (only if needed)

Only create this if the user indicated custom transforms are needed in Step 1.

Follow the pattern from `science/impact_engine/models/interrupted_time_series/transforms.py`.

## Step 8: Create `tests/__init__.py`

Create `science/impact_engine/models/{MODEL_NAME}/tests/__init__.py`:
```python
"""Tests for {model name in human-readable form} model."""
```

## Step 9: Create `tests/test_adapter.py`

Create `science/impact_engine/models/{MODEL_NAME}/tests/test_adapter.py`.

### Required test classes:

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

### Test patterns:
- Use `merge_model_params()` from `impact_engine.models.conftest` for configs needing defaults
- Use `pytest.raises(ExceptionType, match="pattern")` for error tests
- Create test data inline as `pd.DataFrame` (no external fixture files)
- Assert `isinstance(result, ModelResult)` and `result.model_type == "{MODEL_NAME}"`

## Step 10: Update `factory.py`

Edit `science/impact_engine/models/factory.py` to add the import trigger at the bottom, maintaining alphabetical order:

```python
from .interrupted_time_series import InterruptedTimeSeriesAdapter  # noqa: E402, F401
from .metrics_approximation import MetricsApproximationAdapter  # noqa: E402, F401
from .{MODEL_NAME} import {CLASS_NAME}  # noqa: E402, F401
```

The `# noqa: E402, F401` comment is required to suppress ruff warnings.

## Step 11: Update `config_defaults.yaml` (if needed)

If the model has default configuration parameters, add them under `MEASUREMENT.PARAMS` in `science/impact_engine/config_defaults.yaml`. Group with a comment:

```yaml
    # {Human-readable model name} params
    {new_param}: {default_value}
```

Use `null` for REQUIRED parameters. Use actual values for optional parameters with defaults.

## Step 12: Create a feature branch

All work must be done on a feature branch, not on `main`.

```bash
git checkout -b add-model-{MODEL_NAME}
```

Commit all new and modified files with a descriptive message:
```bash
git add science/impact_engine/models/{MODEL_NAME}/ science/impact_engine/models/factory.py science/impact_engine/config_defaults.yaml
git commit -m "Add {MODEL_NAME} measurement model adapter"
```

## Step 13: Run the test suite locally

Run model-specific tests first:
```bash
python -m pytest science/impact_engine/models/{MODEL_NAME}/tests/ -v
```

Then run the full test suite to check for regressions:
```bash
python -m pytest science/impact_engine/tests/ -v
```

Also run the linter (matches CI):
```bash
ruff check science/
```

Fix any failures before proceeding.

## Step 14: Push and create a pull request

Push the branch and create a PR targeting `main`:
```bash
git push -u origin add-model-{MODEL_NAME}
gh pr create --title "Add {MODEL_NAME} measurement model" --body "$(cat <<'EOF'
## Summary
- New measurement model adapter: `{MODEL_NAME}`
- Implements {brief method description}
- Includes adapter, tests, registry wiring, and config defaults

## Test plan
- [ ] Model-specific tests pass
- [ ] Full test suite passes
- [ ] Ruff lint passes
- [ ] GitHub Actions CI passes

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

## Step 15: Verify GitHub Actions pass

After creating the PR, wait for CI and check the result:
```bash
gh pr checks --watch
```

If CI fails, fix the issues, commit, push, and re-check. Do not consider the task complete until CI is green.

## Step 16: Final verification checklist

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
- [ ] Ruff lint passes
- [ ] `config_defaults.yaml` updated if the model has default parameters
- [ ] PR created targeting `main`
- [ ] GitHub Actions CI is green
