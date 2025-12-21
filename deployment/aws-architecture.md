# AWS Architecture - Impact Engine

## Overview

Serverless architecture for running Impact Engine analysis jobs on AWS.

## Architecture Diagram

```mermaid
flowchart LR
    subgraph Client
        A[Client Application]
    end

    subgraph AWS Cloud
        B[API Gateway]
        C[Lambda]
        D[(S3 Bucket<br/>config / data / results)]
        E[ECS Fargate]
        F[(ECR<br/>Impact Engine Image)]
    end

    A -->|1. Upload config/data| B
    B --> C
    C -->|2. Store| D
    C -->|3. Trigger task| E
    F -->|4. Pull image| E
    E -->|5. Read input| D
    E -->|6. Write results| D
    A -->|7. Download results| D
```

## Data Flow

| Step | Action | Service |
|------|--------|---------|
| 1 | Client uploads config and data paths | API Gateway |
| 2 | Lambda stores inputs in S3 | Lambda -> S3 |
| 3 | Lambda triggers ECS Fargate task | Lambda -> ECS |
| 4 | Fargate pulls container image | ECR -> ECS |
| 5 | Container reads input data | ECS -> S3 |
| 6 | Container writes analysis results | ECS -> S3 |
| 7 | Client downloads results | S3 -> Client |

## S3 Bucket Structure

```
s3://impact-engine/
└── {job_id}/
    ├── input/
    │   ├── config.json
    │   └── data/
    └── output/
        └── results/
```

Job-based structure emphasizes the stateless, job-oriented nature of the system.
