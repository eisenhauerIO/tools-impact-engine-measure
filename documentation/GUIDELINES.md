# Documentation Guidelines

## Docs Structure

Each page serves a distinct purpose. Model-specific details belong in notebooks, not in guides.

| Page | Purpose |
|------|---------|
| `README.md` | Package positioning and quick start. Also the docs landing page via `index.md`. |
| `design.md` | Architecture, extensibility, data flow. |
| `usage.md` | General workflow, model-agnostic. Links to notebooks for specifics. |
| `configuration.md` | Parameter reference tables. |
| `api_reference.rst` | Auto-generated from source. Do not hand-edit. |
| Notebooks | One per model. Runnable deep dives with validation. |

---

## Writing Style

All documentation pages follow the tone set by `design.md`.

- Narrative prose with complete sentences. No sentence fragments or bullet-only pages.
- Succinct — every sentence earns its place. No filler, no restating the obvious.
- Structured — use headings, horizontal rules, tables, and code blocks to make pages scannable.
- Symmetric — when multiple items follow a pattern (models, layers, steps), present them in parallel structure (same heading depth, same format, same level of detail).

---

## Text Formatting Conventions

| Category | Format | Examples |
|----------|--------|----------|
| Functions/methods | backticks | `connect()`, `retrieve_business_metrics()` |
| Variables/column names | backticks | `product_id`, `artifact_store` |
| Config keys/values | backticks | `storage_url`, `date_range` |
| File names (no link) | backticks | `engine.py`, `config.yaml` |
| Classes/interfaces (with source) | markdown link | [MetricsManager](path), [MetricsInterface](path) |
| Files (with source) | markdown link | [engine.py](path) |
| Design patterns | bold | **adapter pattern**, **data contracts** |
| Key architectural concepts | bold | **plugin architecture**, **schema transformations** |
| Tools/services | plain text | GitHub Actions, S3 |
| File formats | plain text | YAML, JSON |

1. Use backticks for any code identifier that appears inline in prose
2. Use markdown links when referencing source files, classes, or interfaces that readers might want to navigate to
3. Use bold sparingly for design patterns and key concepts being introduced or emphasized
4. Keep tool and format names in plain text for readability
5. Write in narrative prose with complete sentences. Avoid semicolons and colons.

---

## Architectural Symmetry

The three core layers—Metrics, Models, and Storage—must be treated symmetrically. Each layer follows the same structural pattern:

| Component | Metrics | Models | Storage |
|-----------|---------|--------|---------|
| Interface | `MetricsInterface` | `ModelInterface` | `StorageInterface` |
| Manager | `MetricsManager` | `ModelsManager` | `StorageManager` |
| Registry | `METRICS_REGISTRY` | `MODEL_REGISTRY` | `STORAGE_REGISTRY` |
| Factory | `create_metrics_manager()` | `create_models_manager()` | `create_storage_manager()` |

When extending or modifying one layer, ensure the same pattern applies to all three.

---

## Notebooks

### One notebook per model

Each measurement model gets exactly one demo notebook: `notebooks/demo_{model}.ipynb`.

### Structure

Every notebook follows this step sequence:

1. **Title & Overview** — `# {Model Name} Impact Estimation`, followed by a Workflow Overview listing the steps
2. **Setup** — imports
3. **Step 1: Create Products Catalog** — generate or load products via the catalog simulator
4. **Step 2: Configure** — model-specific configuration explanation, reference config files
5. **Step 3: Run Impact Evaluation** — single call to `evaluate_impact()`
6. **Step 4: Review Results** — load `impact_results.json`, print formatted output
7. **Step 5: Truth Recovery Validation** — compare model estimate against known true effect
8. **Convergence Analysis** — sweep over increasing sample sizes, plot estimate vs truth

### Configs

- Each notebook has matching YAML configs in `notebooks/configs/`
- Naming: `demo_{model}.yaml`, `demo_{model}_baseline.yaml`, `demo_{model}_catalog.yaml`
- Enriched configs use `demo_{model}_enriched.yaml` when applicable

### Output

- Output directory: `notebooks/output/demo_{model}/`
- Created via `Path("output/demo_{model}").mkdir(parents=True, exist_ok=True)`

### Shared utilities

- Reusable plot functions live in `notebooks/notebook_support.py`
- Import as `from notebook_support import plot_convergence`

### Sphinx integration

- Notebooks must run cleanly (`nbsphinx_execute = "always"`)
- Register new notebooks in `index.md` under the Demos toctree
