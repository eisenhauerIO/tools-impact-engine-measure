"""
File Adapter - reads metrics data from CSV or Parquet files.

This adapter enables file-based workflows where upstream processes
produce data files that impact-engine consumes.
"""

import logging
from typing import Any, Dict, Optional

import pandas as pd
from artifact_store import ArtifactStore

from ..base import MetricsInterface
from ..factory import METRICS_REGISTRY


@METRICS_REGISTRY.register_decorator("file")
class FileAdapter(MetricsInterface):
    """Adapter for file-based data sources that implements MetricsInterface.

    Supports CSV and Parquet file formats. The file is expected to contain
    pre-processed data ready for impact analysis.

    Configuration:
        DATA:
            SOURCE:
                type: file
                CONFIG:
                    path: path/to/data.csv
                    # Optional parameters:
                    date_column: date        # Column name for date filtering
                    product_id_column: product_id  # Column name for product IDs
    """

    def __init__(self):
        """Initialize the FileAdapter."""
        self.logger = logging.getLogger(__name__)
        self.is_connected = False
        self.config: Optional[Dict[str, Any]] = None
        self.data: Optional[pd.DataFrame] = None
        self.store: Optional[ArtifactStore] = None
        self.filename: Optional[str] = None

    def connect(self, config: Dict[str, Any]) -> bool:
        """Initialize adapter with configuration parameters.

        Args:
            config: Dictionary containing (lowercase keys, merged via process_config):
                - path: Path to the data file (required)
                - date_column: Column name for dates (optional)
                - product_id_column: Column name for product IDs (optional, default: product_id)

        Returns:
            bool: True if initialization successful

        Raises:
            ValueError: If required configuration is missing
            FileNotFoundError: If the specified file doesn't exist
        """
        path = config.get("path")
        if not path:
            raise ValueError("'path' is required in file adapter configuration")

        # Use artifact store for cloud compatibility (supports local and S3 paths)
        self.store, self.filename = ArtifactStore.from_file_path(path)
        if not self.store.exists(self.filename):
            raise FileNotFoundError(f"Data file not found: {path}")

        self.config = {
            "path": path,
            "date_column": config.get("date_column"),
            "product_id_column": config.get("product_id_column", "product_id"),
        }

        # Pre-load data for validation
        self._load_data()

        self.is_connected = True
        self.logger.info(f"Connected to file source: {path}")
        return True

    def _load_data(self) -> pd.DataFrame:
        """Load data from file (CSV or Parquet).

        Returns:
            DataFrame with loaded data

        Raises:
            ValueError: If file format is not supported
        """
        path = self.config["path"]
        filename_lower = self.filename.lower()

        if filename_lower.endswith(".csv"):
            self.data = self.store.read_csv(self.filename)
        elif filename_lower.endswith((".parquet", ".pq")):
            self.data = self.store.read_parquet(self.filename)
        else:
            raise ValueError("Unsupported file format. Use .csv or .parquet")

        self.logger.info(f"Loaded {len(self.data)} rows from {path}")
        return self.data

    def retrieve_business_metrics(
        self, products: pd.DataFrame, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """Retrieve business metrics from the loaded file.

        For file-based sources, the data is already loaded. This method
        optionally filters by date range and product IDs if configured.

        Args:
            products: DataFrame with product identifiers (can be empty for file sources)
            start_date: Start date in YYYY-MM-DD format (used if DATE_COLUMN configured)
            end_date: End date in YYYY-MM-DD format (used if DATE_COLUMN configured)

        Returns:
            DataFrame with business metrics

        Raises:
            ConnectionError: If adapter not connected
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to file source. Call connect() first.")

        result = self.data.copy()

        # Filter by date if date column is configured
        date_col = self.config.get("date_column")
        if date_col and date_col in result.columns:
            result[date_col] = pd.to_datetime(result[date_col])
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            result = result[(result[date_col] >= start) & (result[date_col] <= end)]
            self.logger.info(
                f"Filtered to {len(result)} rows for date range {start_date} to {end_date}"
            )

        # Filter by products if provided and product_id column exists
        if products is not None and len(products) > 0:
            id_col = self.config.get("product_id_column", "product_id")
            if id_col in result.columns and "product_id" in products.columns:
                product_ids = set(products["product_id"].tolist())
                result = result[result[id_col].isin(product_ids)]
                self.logger.info(f"Filtered to {len(result)} rows for {len(product_ids)} products")

        return self.transform_inbound(result)

    def validate_connection(self) -> bool:
        """Validate that the file source is accessible.

        Returns:
            bool: True if file exists and data is loaded
        """
        if not self.is_connected or self.config is None or self.store is None:
            return False

        return self.store.exists(self.filename) and self.data is not None

    def transform_outbound(
        self, products: pd.DataFrame, start_date: str, end_date: str
    ) -> Dict[str, Any]:
        """Transform impact engine format to file adapter format.

        For file-based sources, this is a pass-through since the file
        already contains the data in the expected format.

        Args:
            products: DataFrame with product identifiers
            start_date: Start date
            end_date: End date

        Returns:
            Dictionary with query parameters
        """
        return {
            "products": products,
            "start_date": start_date,
            "end_date": end_date,
        }

    def transform_inbound(self, external_data: Any) -> pd.DataFrame:
        """Transform file data to impact engine format.

        For file-based sources, this adds metadata fields and ensures
        proper column naming.

        Args:
            external_data: DataFrame read from file

        Returns:
            DataFrame with standardized format
        """
        if not isinstance(external_data, pd.DataFrame):
            raise ValueError("Expected pandas DataFrame from file source")

        result = external_data.copy()

        # Standardize product ID column if needed
        id_col = self.config.get("product_id_column", "product_id")
        if id_col in result.columns and id_col != "product_id":
            result["product_id"] = result[id_col]

        return result
