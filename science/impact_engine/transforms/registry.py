"""
Transform registry for managing data transformation functions.

This module provides a registry pattern similar to the metrics and models
registries, allowing transforms to be registered and retrieved by name.
"""

from typing import Any, Callable, Dict

import pandas as pd

# Type alias for transform functions
TransformFunction = Callable[[pd.DataFrame, Dict[str, Any]], pd.DataFrame]

# Registry of available transforms
TRANSFORM_REGISTRY: Dict[str, TransformFunction] = {}


def get_transform(function_name: str) -> TransformFunction:
    """Get a transform function by name.

    Args:
        function_name: The name of the transform function.

    Returns:
        TransformFunction: The transform function.

    Raises:
        ValueError: If the transform function is not found.
    """
    if function_name not in TRANSFORM_REGISTRY:
        available = list(TRANSFORM_REGISTRY.keys())
        raise ValueError(f"Unknown transform function '{function_name}'. Available: {available}")
    return TRANSFORM_REGISTRY[function_name]


def register_transform(name: str) -> Callable[[TransformFunction], TransformFunction]:
    """Decorator to register a transform function.

    Args:
        name: The name to register the function under.

    Returns:
        Decorator function.

    Example:
        @register_transform("my_transform")
        def my_transform(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
            return df
    """

    def decorator(func: TransformFunction) -> TransformFunction:
        if not callable(func):
            raise ValueError(f"Transform must be callable, got {type(func)}")
        TRANSFORM_REGISTRY[name] = func
        return func

    return decorator


def apply_transform(
    data: pd.DataFrame,
    transform_config: Dict[str, Any],
) -> pd.DataFrame:
    """Apply a transform to data based on configuration.

    Args:
        data: The input DataFrame to transform.
        transform_config: Configuration dict with FUNCTION and PARAMS keys.
            Example: {"FUNCTION": "aggregate_by_date", "PARAMS": {"metric": "revenue"}}

    Returns:
        pd.DataFrame: The transformed data.

    Raises:
        ValueError: If FUNCTION is not specified or not found.
    """
    if "FUNCTION" not in transform_config:
        raise ValueError("Transform config must include 'FUNCTION' key")

    function_name = transform_config["FUNCTION"]
    params = transform_config.get("PARAMS", {})

    transform_fn = get_transform(function_name)
    return transform_fn(data, params)
