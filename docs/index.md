# Impact Engine Documentation

A comprehensive package for evaluating causal impact of product interventions using business metrics and statistical modeling.

```{toctree}
:maxdepth: 2
:caption: Contents:

user-stories
design
data-abstraction-layer
modeling-abstraction-layer
```

## Overview

Impact Engine provides a unified framework for:
- **Metrics Collection**: Retrieve business metrics from various data sources (simulators, databases, APIs)
- **Statistical Modeling**: Apply causal inference models to measure intervention impact
- **Extensible Architecture**: Plugin-based system for custom metrics providers and models

## Quick Start

### Installation

```bash
pip install impact-engine
```

### Basic Usage

```python
from impact_engine import evaluate_impact
import pandas as pd

# Define products to analyze
products = pd.DataFrame({
    'product_id': ['prod1', 'prod2'],
    'name': ['Product 1', 'Product 2']
})

# Run impact analysis
result_path = evaluate_impact(
    config_path='config.json',
    products=products,
    output_path='results/'
)

print(f"Results saved to: {result_path}")
```

## Architecture

Impact Engine follows a layered architecture with clear separation of concerns:

```
┌─────────────────┐
│   engine.py     │  ← Main orchestration layer
│ (evaluate_impact)│
└─────────────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌─────────┐ ┌─────────┐
│ Metrics │ │ Models  │  ← Specialized layers
│ Layer   │ │ Layer   │
└─────────┘ └─────────┘
    │         │
    ▼         ▼
┌─────────┐ ┌─────────┐
│Adapters │ │Adapters │  ← External integrations
└─────────┘ └─────────┘
```

## Indices and tables

* {ref}`genindex`
* {ref}`modindex`
* {ref}`search`