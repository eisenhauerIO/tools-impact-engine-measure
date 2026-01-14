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

        # Drop target columns that already exist to avoid duplicates after rename
        existing_targets = [col for col in inverse.values() if col in result.columns]
        if existing_targets:
            result = result.drop(columns=existing_targets)

        return result.rename(columns=inverse)

    def all_columns(self) -> List[str]:
        """Return all columns (required + optional)."""
        return self.required + self.optional

    def resolve_column(self, df: pd.DataFrame, standard_name: str, source: str = None) -> str:
        """Resolve the actual column name in the DataFrame for a standard field.

        This method enables transforms to work with data from any source by looking
        up the column name dynamically instead of hard-coding specific names.

        The resolution order is:
        1. If source is specified and has a mapping, check for the external name
        2. Check for the standard name directly
        3. Check all known aliases from all source mappings

        Args:
            df: DataFrame to search for the column
            standard_name: The standard/canonical field name (e.g., "product_id")
            source: Optional source type hint (e.g., "catalog_simulator")

        Returns:
            str: The actual column name found in the DataFrame

        Raises:
            ValueError: If no matching column is found

        Example:
            >>> schema = ProductSchema
            >>> # df has 'asin' column from catalog_simulator
            >>> col = schema.resolve_column(df, "product_id", source="catalog_simulator")
            >>> col  # Returns 'asin'
        """
        # Collect all possible names for this standard field
        possible_names = [standard_name]

        # Add source-specific external name if source is specified
        if source and source in self.mappings:
            # Invert mapping to find external name for standard name
            for ext_name, std_name in self.mappings[source].items():
                if std_name == standard_name:
                    possible_names.insert(0, ext_name)  # Prioritize source-specific name

        # Add all known aliases from all sources
        for source_mappings in self.mappings.values():
            for ext_name, std_name in source_mappings.items():
                if std_name == standard_name and ext_name not in possible_names:
                    possible_names.append(ext_name)

        # Find the first matching column in the DataFrame
        for name in possible_names:
            if name in df.columns:
                return name

        raise ValueError(
            f"Cannot resolve column '{standard_name}' in DataFrame. "
            f"Tried: {possible_names}. Available columns: {list(df.columns)}"
        )


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
        "quality_score",
        "metrics_source",
        "retrieval_timestamp",
    ],
    mappings={
        "catalog_simulator": {
            "asin": "product_id",
            "product_identifier": "product_id",
            "ordered_units": "sales_volume",
        },
        "database": {
            "sku": "product_id",
            "units_sold": "sales_volume",
            "total_revenue": "revenue",
        },
    },
)
