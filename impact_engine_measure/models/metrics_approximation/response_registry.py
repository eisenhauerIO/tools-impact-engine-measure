"""Registry for response functions.

Follows the same pattern as catalog-generator's METRICS config:
    RESPONSE:
        FUNCTION: "linear"
        PARAMS:
            coefficient: 0.5
"""

from typing import Callable, Dict, Union

from ...core.registry import FunctionRegistry
from .response_library import linear_response

# Type alias for response functions (can return float or dict of floats)
ResponseFunction = Callable[..., Union[float, Dict[str, float]]]

# Registry of available response functions
RESPONSE_REGISTRY: FunctionRegistry[ResponseFunction] = FunctionRegistry("response function")

# Convenience aliases
get_response_function = RESPONSE_REGISTRY.get
register_response_function = RESPONSE_REGISTRY.register

# Register built-in response functions
RESPONSE_REGISTRY.register("linear", linear_response)
