"""Tests for load_config in core/validation.py."""

import pytest

from impact_engine_measure.core import ConfigValidationError, load_config

_MINIMAL_VALID_CONFIG = {
    "DATA": {
        "SOURCE": {
            "type": "file",
            "CONFIG": {
                "path": "/tmp/products.csv",
            },
        },
    },
    "MEASUREMENT": {
        "MODEL": "difference_in_differences",
        "PARAMS": {},
    },
}


def test_load_config_from_dict_valid():
    """load_config accepts a pre-parsed dict and returns merged config."""
    result = load_config(_MINIMAL_VALID_CONFIG)
    assert isinstance(result, dict)
    assert "DATA" in result
    assert "MEASUREMENT" in result


def test_load_config_none_raises():
    """load_config(None) raises ConfigValidationError — required fields are null."""
    with pytest.raises(ConfigValidationError):
        load_config(None)
