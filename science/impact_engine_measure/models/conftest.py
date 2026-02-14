"""Shared test utilities for model adapter tests."""

from typing import Any, Dict

from impact_engine_measure.core import deep_merge, get_defaults


def merge_model_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Merge user params with defaults from config_defaults.yaml.

    Use this when testing adapters directly without going through
    the full process_config() pipeline.

    Args:
        params: User-provided params dict to merge over defaults.

    Returns:
        Merged params with defaults applied.
    """
    defaults = get_defaults()
    default_params = defaults.get("MEASUREMENT", {}).get("PARAMS", {})
    return deep_merge(default_params, params)
