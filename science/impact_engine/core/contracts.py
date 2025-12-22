"""
Data contracts for impact-engine integration.

This module defines the schemas and field mappings that govern how data flows
between impact-engine and external systems (catalog_simulator, databases, etc.).

These contracts enforce that libraries integrate ONLY through standardized schemas,
preventing tight coupling and enabling independent evolution.
"""

from dataclasses import dataclass, field
from typing import Dict, List

import pandas as pd


@dataclass
class Schema:
    """Base schema with validation and bidirectional field mapping."""

    required: List[str]
    optional: List[str] = field(default_factory=list)
    # Field mappings: {source_type: {external_name: standard_name}}
    mappings: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def validate(self, df: pd.DataFrame) -> bool:
        """Check DataFrame has required columns."""
        missing = set(self.required) - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        return True

    def from_external(self, df: pd.DataFrame, source: str) -> pd.DataFrame:
        """Convert external format to standard schema."""
        if source not in self.mappings:
            return df.copy()
        result = df.copy()
        return result.rename(columns=self.mappings[source])

    def to_external(self, df: pd.DataFrame, target: str) -> pd.DataFrame:
        """Convert standard schema to external format."""
        if target not in self.mappings:
            return df.copy()
        # Invert the mapping: {standard_name: external_name}
        inverse = {v: k for k, v in self.mappings[target].items()}
        result = df.copy()
        return result.rename(columns=inverse)

    def all_columns(self) -> List[str]:
        """Return all columns (required + optional)."""
        return self.required + self.optional


# Product schema: defines product identifiers
ProductSchema = Schema(
    required=["product_id"],
    optional=["name", "category", "price"],
    mappings={
        "catalog_simulator": {"asin": "product_id"},
        "database": {"sku": "product_id", "product_name": "name"},
    },
)

# Metrics schema: defines business metrics output
MetricsSchema = Schema(
    required=["product_id", "date", "sales_volume", "revenue"],
    optional=[
        "name",
        "category",
        "price",
        "inventory_level",
        "customer_engagement",
        "metrics_source",
        "retrieval_timestamp",
    ],
    mappings={
        "catalog_simulator": {
            "asin": "product_id",
            "ordered_units": "sales_volume",
        },
        "database": {
            "sku": "product_id",
            "units_sold": "sales_volume",
            "total_revenue": "revenue",
        },
    },
)
