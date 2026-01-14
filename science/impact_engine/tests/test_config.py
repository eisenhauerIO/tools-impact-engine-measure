"""Tests for centralized configuration processing."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from impact_engine.config import (
    ConfigurationError,
    deep_merge,
    load_defaults,
    process_config,
    validate_config,
    _require,
    _validate_date_format,
    _validate_model_params,
    get_source_config,
    get_measurement_params,
    get_transform_config,
)


class TestLoadDefaults:
    """Tests for load_defaults function."""

    def test_load_defaults_returns_dict(self):
        """Test that load_defaults returns a dictionary."""
        defaults = load_defaults()
        assert isinstance(defaults, dict)

    def test_load_defaults_has_required_sections(self):
        """Test that defaults have required sections."""
        defaults = load_defaults()
        assert "DATA" in defaults
        assert "MEASUREMENT" in defaults

    def test_load_defaults_has_model_params(self):
        """Test that defaults have model-specific parameters."""
        defaults = load_defaults()
        assert "PARAMS" in defaults["MEASUREMENT"]
        assert "interrupted_time_series" in defaults["MEASUREMENT"]["PARAMS"]
        assert "metrics_approximation" in defaults["MEASUREMENT"]["PARAMS"]


class TestDeepMerge:
    """Tests for deep_merge function."""

    def test_deep_merge_basic(self):
        """Test basic merge of two dicts."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = deep_merge(base, override)

        assert result["a"] == 1
        assert result["b"] == 3
        assert result["c"] == 4

    def test_deep_merge_nested(self):
        """Test deep merge of nested dicts."""
        base = {"outer": {"a": 1, "b": 2}}
        override = {"outer": {"b": 3, "c": 4}}
        result = deep_merge(base, override)

        assert result["outer"]["a"] == 1
        assert result["outer"]["b"] == 3
        assert result["outer"]["c"] == 4

    def test_deep_merge_preserves_originals(self):
        """Test that deep_merge doesn't modify originals."""
        base = {"a": {"x": 1}}
        override = {"a": {"y": 2}}

        result = deep_merge(base, override)

        assert base == {"a": {"x": 1}}
        assert override == {"a": {"y": 2}}

    def test_deep_merge_override_replaces_non_dict(self):
        """Test that override replaces non-dict values completely."""
        base = {"a": [1, 2, 3]}
        override = {"a": [4, 5]}
        result = deep_merge(base, override)

        assert result["a"] == [4, 5]


class TestRequire:
    """Tests for _require helper."""

    def test_require_simple_path(self):
        """Test _require with simple path."""
        config = {"DATA": "value"}
        _require(config, "DATA", "Error")  # Should not raise

    def test_require_nested_path(self):
        """Test _require with nested path."""
        config = {"DATA": {"SOURCE": {"TYPE": "simulator"}}}
        _require(config, "DATA.SOURCE.TYPE", "Error")  # Should not raise

    def test_require_missing_raises(self):
        """Test _require raises for missing field."""
        config = {"DATA": {}}
        with pytest.raises(ConfigurationError, match="Missing field"):
            _require(config, "DATA.SOURCE", "Missing field")

    def test_require_null_raises(self):
        """Test _require raises for null value."""
        config = {"DATA": {"PATH": None}}
        with pytest.raises(ConfigurationError, match="Null value"):
            _require(config, "DATA.PATH", "Null value")

    def test_require_empty_string_raises(self):
        """Test _require raises for empty string."""
        config = {"DATA": {"PATH": ""}}
        with pytest.raises(ConfigurationError, match="Empty"):
            _require(config, "DATA.PATH", "Empty")


class TestValidateDateFormat:
    """Tests for _validate_date_format helper."""

    def test_valid_date(self):
        """Test valid date format."""
        result = _validate_date_format("2024-01-15", "test_date")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_invalid_format_raises(self):
        """Test invalid date format raises."""
        with pytest.raises(ConfigurationError, match="Expected YYYY-MM-DD"):
            _validate_date_format("01-15-2024", "test_date")

    def test_invalid_date_raises(self):
        """Test invalid date raises."""
        with pytest.raises(ConfigurationError, match="test_date"):
            _validate_date_format("2024-13-45", "test_date")


class TestValidateModelParams:
    """Tests for _validate_model_params function."""

    def test_known_model_valid_params(self):
        """Test validation passes for known model with valid params."""
        params = {
            "dependent_variable": "revenue",
            "intervention_date": "2024-01-15",
            "order": (1, 0, 0),
            "seasonal_order": (0, 0, 0, 0),
        }
        # Should not raise
        _validate_model_params("interrupted_time_series", params)

    def test_known_model_unexpected_params_raises(self):
        """Test validation raises for unexpected params."""
        params = {
            "dependent_variable": "revenue",
            "intervention_date": "2024-01-15",
            "unknown_param": "value",
        }
        with pytest.raises(ConfigurationError, match="Unexpected parameters"):
            _validate_model_params("interrupted_time_series", params)

    def test_unknown_model_skips_validation(self):
        """Test that unknown models skip validation."""
        params = {"any": "params", "are": "allowed"}
        # Should not raise for unknown model
        _validate_model_params("custom_model", params)

    def test_required_non_null_raises(self):
        """Test that required non-null params raise if null."""
        params = {"intervention_date": None}
        with pytest.raises(ConfigurationError, match="must be provided by user"):
            _validate_model_params(
                "interrupted_time_series",
                params,
                required_non_null={"intervention_date"},
            )


class TestProcessConfig:
    """Tests for process_config function."""

    def test_process_config_merges_defaults(self):
        """Test that process_config merges defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "DATA": {
                    "SOURCE": {
                        "TYPE": "simulator",
                        "CONFIG": {
                            "PATH": "products.csv",
                            "START_DATE": "2024-01-01",
                            "END_DATE": "2024-01-31",
                        },
                    },
                },
                "MEASUREMENT": {
                    "MODEL": "interrupted_time_series",
                    "PARAMS": {"intervention_date": "2024-01-15"},
                },
            }
            config_path = Path(tmpdir) / "config.yaml"
            with open(config_path, "w") as f:
                yaml.dump(config, f)

            result = process_config(str(config_path))

            # User values preserved
            assert result["MEASUREMENT"]["PARAMS"]["intervention_date"] == "2024-01-15"
            # Defaults merged in
            assert "dependent_variable" in result["MEASUREMENT"]["PARAMS"]
            assert "order" in result["MEASUREMENT"]["PARAMS"]

    def test_process_config_converts_lists_to_tuples(self):
        """Test that order params are converted to tuples."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "DATA": {
                    "SOURCE": {
                        "TYPE": "simulator",
                        "CONFIG": {
                            "PATH": "products.csv",
                            "START_DATE": "2024-01-01",
                            "END_DATE": "2024-01-31",
                        },
                    },
                },
                "MEASUREMENT": {
                    "MODEL": "interrupted_time_series",
                    "PARAMS": {"intervention_date": "2024-01-15"},
                },
            }
            config_path = Path(tmpdir) / "config.yaml"
            with open(config_path, "w") as f:
                yaml.dump(config, f)

            result = process_config(str(config_path))

            # Should be tuples, not lists
            assert isinstance(result["MEASUREMENT"]["PARAMS"]["order"], tuple)
            assert isinstance(result["MEASUREMENT"]["PARAMS"]["seasonal_order"], tuple)

    def test_process_config_injects_enrichment_params(self):
        """Test that enrichment params are injected into transform."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "DATA": {
                    "SOURCE": {
                        "TYPE": "simulator",
                        "CONFIG": {
                            "PATH": "products.csv",
                            "START_DATE": "2024-01-01",
                            "END_DATE": "2024-01-31",
                        },
                    },
                    "ENRICHMENT": {
                        "function": "boost",
                        "params": {"enrichment_start": "2024-01-15"},
                    },
                    "TRANSFORM": {"FUNCTION": "prepare_simulator_for_approximation"},
                },
                "MEASUREMENT": {
                    "MODEL": "metrics_approximation",
                    "PARAMS": {},
                },
            }
            config_path = Path(tmpdir) / "config.yaml"
            with open(config_path, "w") as f:
                yaml.dump(config, f)

            result = process_config(str(config_path))

            # enrichment_start should be injected
            assert result["DATA"]["TRANSFORM"]["PARAMS"]["enrichment_start"] == "2024-01-15"

    def test_process_config_file_not_found(self):
        """Test that missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            process_config("/nonexistent/config.yaml")

    def test_process_config_invalid_raises(self):
        """Test that invalid config raises ConfigurationError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"invalid": "config"}
            config_path = Path(tmpdir) / "config.yaml"
            with open(config_path, "w") as f:
                yaml.dump(config, f)

            with pytest.raises(ConfigurationError):
                process_config(str(config_path))


class TestValidateConfig:
    """Tests for validate_config function."""

    def test_validate_config_missing_data(self):
        """Test validation fails for missing DATA."""
        with pytest.raises(ConfigurationError, match="DATA"):
            validate_config({"MEASUREMENT": {}})

    def test_validate_config_missing_measurement(self):
        """Test validation fails for missing MEASUREMENT."""
        config = {
            "DATA": {
                "SOURCE": {
                    "TYPE": "simulator",
                    "CONFIG": {
                        "PATH": "x.csv",
                        "START_DATE": "2024-01-01",
                        "END_DATE": "2024-01-31",
                    },
                }
            }
        }
        with pytest.raises(ConfigurationError, match="MEASUREMENT"):
            validate_config(config)

    def test_validate_config_date_order(self):
        """Test validation fails when start > end date."""
        config = {
            "DATA": {
                "SOURCE": {
                    "TYPE": "simulator",
                    "CONFIG": {
                        "PATH": "x.csv",
                        "START_DATE": "2024-12-31",
                        "END_DATE": "2024-01-01",
                    },
                }
            },
            "MEASUREMENT": {"MODEL": "metrics_approximation", "PARAMS": {}},
        }
        with pytest.raises(ConfigurationError, match="must be before"):
            validate_config(config)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_source_config(self):
        """Test get_source_config extracts correctly."""
        config = {
            "DATA": {
                "SOURCE": {"CONFIG": {"PATH": "test.csv", "START_DATE": "2024-01-01"}}
            }
        }
        result = get_source_config(config)
        assert result["PATH"] == "test.csv"

    def test_get_measurement_params(self):
        """Test get_measurement_params extracts correctly."""
        config = {
            "MEASUREMENT": {"MODEL": "its", "PARAMS": {"intervention_date": "2024-01-15"}}
        }
        result = get_measurement_params(config)
        assert result["intervention_date"] == "2024-01-15"

    def test_get_transform_config_default(self):
        """Test get_transform_config returns default passthrough."""
        config = {"DATA": {}}
        result = get_transform_config(config)
        assert result["FUNCTION"] == "passthrough"
