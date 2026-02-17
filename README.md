# Impact Engine

[![CI](https://github.com/eisenhauerIO/tools-impact-engine-measure/actions/workflows/ci.yaml/badge.svg)](https://github.com/eisenhauerIO/tools-impact-engine-measure/actions/workflows/ci.yaml)
[![Docs](https://github.com/eisenhauerIO/tools-impact-engine-measure/actions/workflows/docs.yml/badge.svg?branch=main)](https://github.com/eisenhauerIO/tools-impact-engine-measure/actions/workflows/docs.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/eisenhauerIO/tools-impact-engine-measure/blob/main/LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Slack](https://img.shields.io/badge/Slack-Join%20Us-4A154B?logo=slack)](https://join.slack.com/t/eisenhauerioworkspace/shared_invite/zt-3lxtc370j-XLdokfTkno54wfhHVxvEfA)

*Centralizing causal impact measurement behind one stable interface*

Change your causal inference method and you're rewriting data connectors, updating downstream consumers, and debugging broken pipelines — even when the business question hasn't changed.

**Impact Engine** manages the ***full measurement pipeline***, not just the estimator. A single YAML config defines your data source, estimation method, storage backend, and output destination — swap any component by changing one line. Custom adapters plug in proprietary data sources and storage without touching the core engine, and every run produces a ***self-describing result bundle*** so downstream teams can consume results without knowing or caring whether the methodology changed last week.

Under the hood it wraps [statsmodels](https://www.statsmodels.org/), [causalml](https://causalml.readthedocs.io/), and [pysyncon](https://sdfordham.github.io/pysyncon/) today, with an extension point for any estimator. Improve your methods continuously, make them available to every team from one place.

## Quick Start

```bash
pip install git+https://github.com/eisenhauerIO/tools-impact-engine-measure.git
```

```python
from impact_engine_measure import evaluate_impact

results_path = evaluate_impact(config_path="config.yaml")
```

## Documentation

| Guide | Description |
|-------|-------------|
| [Usage](https://eisenhauerio.github.io/tools-impact-engine-measure/usage.html) | Getting started with basic workflow |
| [Configuration](https://eisenhauerio.github.io/tools-impact-engine-measure/configuration.html) | All configuration options |
| [Design](https://eisenhauerio.github.io/tools-impact-engine-measure/design.html) | System design and architecture |
