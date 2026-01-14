"""Registry for response functions.

Follows the same pattern as catalog-generator's METRICS config:
    RESPONSE:
        FUNCTION: "linear"
        PARAMS:
            coefficient: 0.5
"""

from typing import Callable, Dict

from .response_library import linear_response

# Registry of available response functions
RESPONSE_FUNCTIONS: Dict[str, Callable] = {
    "linear": linear_response,
}


def get_response_function(name: str) -> Callable:
    """Get a response function by name.

    Args:
        name: Name of the response function (e.g., "linear")

    Returns:
        Callable: The response function

    Raises:
        ValueError: If the response function name is not registered
    """
    if name not in RESPONSE_FUNCTIONS:
        available = list(RESPONSE_FUNCTIONS.keys())
        raise ValueError(f"Unknown response function '{name}'. Available: {available}")
    return RESPONSE_FUNCTIONS[name]


def register_response_function(name: str, func: Callable) -> None:
    """Register a custom response function.

    Args:
        name: Name to register the function under
        func: Response function to register
            Must accept (delta_metric: float, baseline_outcome: float, **kwargs)
            and return float

    Raises:
        ValueError: If the function doesn't have the expected signature
    """
    if not callable(func):
        raise ValueError(f"Response function must be callable, got {type(func)}")
    RESPONSE_FUNCTIONS[name] = func
