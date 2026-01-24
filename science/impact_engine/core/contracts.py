"""
Data contracts for impact-engine integration.

This module defines the schemas and field mappings that govern how data flows
between impact-engine and external systems (catalog_simulator, databases, etc.).

These contracts enforce that libraries integrate ONLY through standardized schemas,
preventing tight coupling and enabling independent evolution.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd


@dataclass
class ColumnContract:
    """Single column specification with aliases and optional type validation.

    Enables auto-detection of columns by standard name or known aliases,
    eliminating the need for manual column detection logic.

    Example:
        product_id_contract = ColumnContract(
            standard_name="product_id",
            aliases=["asin", "sku", "product_identifier"],
            dtype="object",
        )
        # Find column in DataFrame
        col_name = product_id_contract.find_in_df(df)
        # Normalize to standard name
        df = product_id_contract.normalize(df)
    """

    standard_name: str
    aliases: List[str] = field(default_factory=list)
    dtype: Optional[str] = None  # "int64", "float64", "datetime64", "object"
    required: bool = True

    def find_in_df(self, df: pd.DataFrame) -> Optional[str]:
        """Find column in DataFrame by standard name or alias.

        Args:
            df: DataFrame to search

        Returns:
            Column name if found, None otherwise
        """
        candidates = [self.standard_name] + self.aliases
        for col in candidates:
            if col in df.columns:
                return col
        return None

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rename detected column to standard name.

        Args:
            df: DataFrame to normalize

        Returns:
            DataFrame with column renamed to standard_name (if found and different)
        """
        detected = self.find_in_df(df)
        if detected and detected != self.standard_name:
            return df.rename(columns={detected: self.standard_name})
        return df

    def validate_presence(self, df: pd.DataFrame) -> bool:
        """Check if column (or alias) exists in DataFrame.

        Args:
            df: DataFrame to validate

        Returns:
            True if column found, False otherwise
        """
        return self.find_in_df(df) is not None


@dataclass
class Schema:
    """Base schema with validation and bidirectional field mapping.

    Supports two modes:
    1. Simple mode: Define required/optional columns and mappings directly
    2. Contract mode: Use ColumnContract for advanced column detection

    The get_column() and normalize() methods work with both modes,
    using mappings to build implicit ColumnContracts when needed.
    """

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

    def get_column(self, df: pd.DataFrame, standard_name: str) -> Optional[str]:
        """Find actual column name in DataFrame for a standard field.

        Searches for the standard name first, then checks all known aliases
        from the mappings.

        Args:
            df: DataFrame to search
            standard_name: The standard column name to find

        Returns:
            Actual column name if found, None otherwise

        Example:
            col = MetricsSchema.get_column(df, "product_id")
            # Returns "product_id", "asin", or "product_identifier" depending on what exists
        """
        # Check standard name first
        if standard_name in df.columns:
            return standard_name

        # Build aliases from all source mappings
        aliases = []
        for source_mapping in self.mappings.values():
            for external_name, mapped_standard in source_mapping.items():
                if mapped_standard == standard_name and external_name not in aliases:
                    aliases.append(external_name)

        # Check aliases
        for alias in aliases:
            if alias in df.columns:
                return alias

        return None

    def normalize(self, df: pd.DataFrame, source: Optional[str] = None) -> pd.DataFrame:
        """Auto-detect and rename columns to standard names.

        If source is provided, uses that source's mapping. Otherwise,
        attempts to detect columns from all known aliases.

        Args:
            df: DataFrame to normalize
            source: Optional source type for targeted normalization

        Returns:
            DataFrame with columns renamed to standard names

        Example:
            # Normalize from known source
            df = MetricsSchema.normalize(df, source="catalog_simulator")

            # Auto-detect and normalize
            df = MetricsSchema.normalize(df)
        """
        if source:
            return self.from_external(df, source)

        # Auto-detect mode: rename any alias columns to standard names
        result = df.copy()
        renames = {}

        for standard_name in self.required + self.optional:
            if standard_name in result.columns:
                continue  # Already has standard name

            # Find alias in any source mapping
            for source_mapping in self.mappings.values():
                for external_name, mapped_standard in source_mapping.items():
                    if mapped_standard == standard_name and external_name in result.columns:
                        renames[external_name] = standard_name
                        break

        if renames:
            result = result.rename(columns=renames)

        return result


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

# Transform schema: defines columns for approximation transforms
TransformSchema = Schema(
    required=["product_id", "date"],
    optional=["quality_score", "revenue", "sales_volume"],
    mappings={
        "catalog_simulator": {
            "asin": "product_id",
            "product_identifier": "product_id",
            "ordered_units": "sales_volume",
        },
    },
)
