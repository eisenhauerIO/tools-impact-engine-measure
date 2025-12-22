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

## Architecture

Impact Engine follows a clean three-layer architecture with plugin-based extensibility.

### System Overview

```mermaid
flowchart TB
    subgraph Input["INPUT"]
        Config["config.yaml"]
        Products["products.csv"]
    end

    subgraph Engine["ENGINE LAYER"]
        direction TB
        EI["evaluate_impact()"]
        EI --> Parse["Parse & Validate Config"]
        Parse --> Job["Create Job Container"]
        Job --> Orchestrate["Orchestrate Workflow"]
    end

    subgraph DataLayer["DATA LAYER"]
        direction TB
        MM["MetricsManager"]
        MM --> MI["MetricsInterface"]
        MI --> CS["CatalogSimulator"]
        MI --> DB["DatabaseAdapter"]
        MI --> API["APIAdapter"]
    end

    subgraph ModelLayer["MODELS LAYER"]
        direction TB
        MoM["ModelsManager"]
        MoM --> Mo["Model"]
        Mo --> ITS["InterruptedTimeSeries"]
        Mo --> CI["CausalImpact"]
        Mo --> RD["RegressionDiscontinuity"]
    end

    subgraph Core["CORE"]
        direction LR
        Contracts["contracts.py"]
        Bridge["config_bridge.py"]
    end

    subgraph External["EXTERNAL SYSTEMS"]
        direction LR
        Sim["online_retail_simulator"]
        Stats["statsmodels"]
        Store["artifact_store"]
    end

    subgraph Output["OUTPUT"]
        Results["impact_results.json"]
    end

    Config --> Engine
    Products --> Engine
    Engine --> DataLayer
    Engine --> ModelLayer
    DataLayer <--> Core
    ModelLayer <--> Core
    DataLayer --> External
    ModelLayer --> External
    Engine --> Store
    Engine --> Output

    style Engine fill:#e1f5fe
    style DataLayer fill:#f3e5f5
    style ModelLayer fill:#fff3e0
    style Core fill:#e8f5e9
    style External fill:#fafafa
```

### Data Flow Pipeline

```mermaid
flowchart LR
    subgraph Input
        C["Config"]
        P["Products"]
    end

    subgraph Metrics["Metrics Layer"]
        TO1["transform_outbound()"]
        Retrieve["retrieve_metrics()"]
        TI1["transform_inbound()"]
    end

    subgraph Aggregate
        Agg["Group by Date"]
    end

    subgraph Models["Models Layer"]
        TO2["transform_outbound()"]
        Fit["fit()"]
        TI2["transform_inbound()"]
    end

    subgraph Output
        R["Results JSON"]
    end

    C --> TO1
    P --> TO1
    TO1 --> Retrieve
    Retrieve --> TI1
    TI1 --> Agg
    Agg --> TO2
    TO2 --> Fit
    Fit --> TI2
    TI2 --> R

    style Metrics fill:#f3e5f5
    style Models fill:#fff3e0
```

### Design Principles

```mermaid
mindmap
  root((Impact Engine))
    Separation of Concerns
      Engine orchestrates
      Metrics retrieves data
      Models applies statistics
      Core provides contracts
    Configuration-Driven
      YAML defines behavior
      Non-technical friendly
      Version controllable
    Plugin Architecture
      Interface + Registry
      Open/Closed Principle
      Extend without modifying
    Explicit Transformations
      transform_outbound
      transform_inbound
      Clear coupling points
    Fail-Fast Validation
      Config validation
      Connection validation
      Data schema validation
    Artifact Lineage
      Job-based storage
      Full reproducibility
      Audit trail
```

### Plugin Architecture

```mermaid
flowchart TB
    subgraph Registry["REGISTRY PATTERN"]
        direction TB

        subgraph MetricsRegistry["MetricsManager"]
            MR["register_metrics()"]
            MG["get_metrics_source()"]
        end

        subgraph ModelsRegistry["ModelsManager"]
            MoR["register_model()"]
            MoG["get_model()"]
        end
    end

    subgraph Adapters["METRICS ADAPTERS"]
        MI["MetricsInterface\n(ABC)"]
        MI --> A1["CatalogSimulator"]
        MI --> A2["Database"]
        MI --> A3["REST API"]
    end

    subgraph Models["MODEL IMPLEMENTATIONS"]
        M["Model\n(ABC)"]
        M --> M1["InterruptedTimeSeries"]
        M --> M2["CausalImpact"]
        M --> M3["RegressionDiscontinuity"]
    end

    MetricsRegistry --> Adapters
    ModelsRegistry --> Models

    style MI fill:#e1bee7
    style M fill:#ffcc80
```

## Documentation

- [User Stories](documentation/user-stories.md)
- [Configuration](documentation/configuration.md)
- [Design](documentation/design.md)

## License

MIT
