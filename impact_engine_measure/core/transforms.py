"""
Transform registry for managing data transformation functions.

This module provides a registry pattern allowing transforms to be registered
and retrieved by name. Transforms are colocated with their adapters but
register themselves here for config-driven lookup.
"""

from typing import Any, Callable, Dict

import pandas as pd

from .registry import FunctionRegistry

# Type alias for transform functions
TransformFunction = Callable[[pd.DataFrame, Dict[str, Any]], pd.DataFrame]

# Registry of available transforms
TRANSFORM_REGISTRY: FunctionRegistry[TransformFunction] = FunctionRegistry("transform")

# Convenience aliases
get_transform = TRANSFORM_REGISTRY.get
register_transform = TRANSFORM_REGISTRY.register_decorator


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


@register_transform("passthrough")
def passthrough(data: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """Pass data through unchanged.

    Useful when no transformation is needed but a transform must be specified.

    Args:
        data: Input DataFrame.
        params: Unused parameters.

    Returns:
        pd.DataFrame: The input data unchanged.
    """
    return data
