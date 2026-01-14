"""Tests for response functions."""

import pytest

from impact_engine.models.metrics_approximation.response_library import linear_response
from impact_engine.models.metrics_approximation.response_registry import (
    RESPONSE_FUNCTIONS,
    get_response_function,
    register_response_function,
)


class TestLinearResponse:
    """Tests for linear_response function."""

    def test_basic_calculation(self):
        """Linear response computes coefficient * delta * baseline."""
        result = linear_response(0.4, 100, coefficient=0.5)
        assert result == 20.0  # 0.4 * 100 * 0.5

    def test_default_coefficient(self):
        """Default coefficient is 1.0."""
        result = linear_response(0.5, 200)
        assert result == 100.0  # 0.5 * 200 * 1.0

    def test_zero_delta(self):
        """Zero metric change results in zero impact."""
        result = linear_response(0.0, 100, coefficient=0.5)
        assert result == 0.0

    def test_negative_delta(self):
        """Negative metric change results in negative impact."""
        result = linear_response(-0.2, 100, coefficient=0.5)
        assert result == -10.0  # -0.2 * 100 * 0.5

    def test_large_coefficient(self):
        """Large coefficient scales impact appropriately."""
        result = linear_response(0.1, 100, coefficient=2.0)
        assert result == 20.0  # 0.1 * 100 * 2.0

    def test_zero_baseline(self):
        """Zero baseline results in zero impact."""
        result = linear_response(0.5, 0, coefficient=0.5)
        assert result == 0.0


class TestResponseRegistry:
    """Tests for response function registry."""

    def test_get_linear_function(self):
        """Can retrieve linear response function by name."""
        func = get_response_function("linear")
        assert func is linear_response

    def test_unknown_function_raises(self):
        """Unknown function name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown response function"):
            get_response_function("nonexistent")

    def test_error_message_includes_available(self):
        """Error message includes list of available functions."""
        with pytest.raises(ValueError, match="Available:"):
            get_response_function("nonexistent")

    def test_register_custom_function(self):
        """Can register a custom response function."""

        def custom_response(delta_metric: float, baseline_outcome: float, **kwargs) -> float:
            return delta_metric * 2

        register_response_function("custom", custom_response)

        assert "custom" in RESPONSE_FUNCTIONS
        func = get_response_function("custom")
        assert func(0.5, 100) == 1.0

        # Cleanup
        del RESPONSE_FUNCTIONS["custom"]

    def test_register_non_callable_raises(self):
        """Registering non-callable raises ValueError."""
        with pytest.raises(ValueError, match="must be callable"):
            register_response_function("bad", "not a function")

    def test_linear_is_registered(self):
        """Linear function is registered by default."""
        assert "linear" in RESPONSE_FUNCTIONS
