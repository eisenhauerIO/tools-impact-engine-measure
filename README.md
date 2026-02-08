# Impact Engine

[![Tests](https://github.com/eisenhauerIO/tools-impact-engine/actions/workflows/tests.yml/badge.svg)](https://github.com/eisenhauerIO/tools-impact-engine/actions/workflows/tests.yml)
[![Build Documentation](https://github.com/eisenhauerIO/tools-impact-engine/actions/workflows/docs.yml/badge.svg?branch=main)](https://github.com/eisenhauerIO/tools-impact-engine/actions/workflows/docs.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/eisenhauerIO/tools-impact-engine/blob/main/LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Slack](https://img.shields.io/badge/Slack-Join%20Us-4A154B?logo=slack)](https://join.slack.com/t/eisenhauerioworkspace/shared_invite/zt-3lxtc370j-XLdokfTkno54wfhHVxvEfA)

Evaluate **causal impact** of product interventions using business metrics and statistical modeling.

Impact Engine is adapter-based. Each measurement model is a thin wrapper around an established statistical library—not a reimplementation. The engine is extensible in three dimensions: data sources, measurement models, and storage backends all plug in independently through a common interface and decorator-based registry. Custom adapters can live in private repositories. A single YAML configuration file selects all adapters, and the output contract (`impact_results.json` + `manifest.json`) is standardized across models, making results integrable into downstream workflows.

## Installation

```bash
pip install impact-engine
```

## Quick Start

```python
from impact_engine import evaluate_impact

# Products path is specified in `config.yaml` under DATA.PATH
result_path = evaluate_impact(
    config_path="config.yaml",
    storage_url="./results"
)
```

## Documentation

| Guide | Description |
|-------|-------------|
| [Usage](documentation/usage.md) | Getting started with basic workflow |
| [Configuration](documentation/configuration.md) | All configuration options |
| [Design](documentation/design.md) | System design & architecture |

## License

MIT
