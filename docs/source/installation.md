# Installation

## Requirements

- Python 3.10 or higher
- pip

## Install from PyPI

```bash
pip install impact-engine-measure
```

## Install from Source

```bash
git clone https://github.com/eisenhauerIO/tools-impact-engine.git
cd tools-impact-engine
pip install -e ".[dev]"
```

## Verify Installation

```python
from impact_engine_measure import evaluate_impact
print("impact-engine-measure installed successfully")
```

## Development Setup

The project uses [Hatch](https://hatch.pypa.io/) for environment management.

```bash
pip install hatch
hatch env create
```

Install pre-commit hooks:

```bash
hatch run pre-commit install
```

Run tests and linting:

```bash
hatch run test
hatch run lint
```

Build the documentation:

```bash
hatch run docs:build
```
