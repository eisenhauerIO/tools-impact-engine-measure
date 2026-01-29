# Showcase Documentation Guidelines

Guidelines for writing and maintaining documentation in this directory.

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

## Rules

1. Use backticks for any code identifier that appears inline in prose
2. Use markdown links when referencing source files, classes, or interfaces that readers might want to navigate to
3. Use bold sparingly for design patterns and key concepts being introduced or emphasized
4. Keep tool and format names in plain text for readability
5. Write in narrative prose with complete sentences. Avoid semicolons and colons.

## Architectural Symmetry

The three core layers—Metrics, Models, and Storage—must be treated symmetrically. Each layer follows the same structural pattern:

| Component | Metrics | Models | Storage |
|-----------|---------|--------|---------|
| Interface | `MetricsInterface` | `ModelInterface` | `StorageInterface` |
| Manager | `MetricsManager` | `ModelsManager` | `StorageManager` |
| Registry | `METRICS_REGISTRY` | `MODEL_REGISTRY` | `STORAGE_REGISTRY` |
| Factory | `create_metrics_manager()` | `create_models_manager()` | `create_storage_manager()` |

When extending or modifying one layer, ensure the same pattern applies to all three.
