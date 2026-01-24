# Impact Engine

Evaluate causal impact of product interventions using business metrics and statistical modeling.

## Installation

```bash
pip install impact-engine
```

## Quick Start

```python
from impact_engine import evaluate_impact

# Products path is specified in config.yaml under DATA.PATH
result_path = evaluate_impact(
    config_path='config.yaml',
    storage_url='./results'
)
```

## Documentation

| Guide | Description |
|-------|-------------|
| [Usage](documentation/usage.md) | Getting started with basic workflow |
| [Configuration](documentation/configuration.md) | All configuration options |
| [Architecture](documentation/architecture.md) | Code & deployment architecture |

## License

MIT
