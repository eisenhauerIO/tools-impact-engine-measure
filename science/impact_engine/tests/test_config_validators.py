"""Tests for pluggable configuration validators."""

import pytest

from impact_engine.config import (
    ConfigError,
    ConfigValidator,
    DataSourceValidator,
    ITSParamsValidator,
    MeasurementValidator,
    MetricsApproximationParamsValidator,
    TransformValidator,
    get_validator,
    list_validators,
    register_validator,
    validate_config_with_validators,
)


class TestConfigError:
    """Tests for ConfigError dataclass."""

    def test_str_without_section(self):
        """Test string representation without section."""
        error = ConfigError("field_name", "error message")
        assert str(error) == "field_name: error message"

    def test_str_with_section(self):
        """Test string representation with section."""
        error = ConfigError("field_name", "error message", "DATA.SOURCE")
        assert str(error) == "DATA.SOURCE.field_name: error message"


class TestValidatorRegistry:
    """Tests for validator registry."""

    def test_list_validators(self):
        """Test listing registered validators."""
        validators = list_validators()
        assert "DATA.SOURCE" in validators
        assert "DATA.TRANSFORM" in validators
        assert "MEASUREMENT" in validators
        assert "MEASUREMENT.interrupted_time_series" in validators
        assert "MEASUREMENT.metrics_approximation" in validators

    def test_get_validator_exists(self):
        """Test getting a registered validator."""
        validator = get_validator("DATA.SOURCE")
        assert validator is not None
        assert isinstance(validator, DataSourceValidator)

    def test_get_validator_not_exists(self):
        """Test getting a non-existent validator."""
        validator = get_validator("NONEXISTENT")
        assert validator is None

    def test_register_custom_validator(self):
        """Test registering a custom validator."""

        @register_validator("CUSTOM.SECTION")
        class CustomValidator(ConfigValidator):
            def validate(self, config):
                return []

        try:
            validators = list_validators()
            assert "CUSTOM.SECTION" in validators

            validator = get_validator("CUSTOM.SECTION")
            assert validator is not None
            assert isinstance(validator, CustomValidator)
        finally:
            # Clean up
            from impact_engine.config.validators import _VALIDATOR_REGISTRY

            del _VALIDATOR_REGISTRY["CUSTOM.SECTION"]


class TestDataSourceValidator:
    """Tests for DataSourceValidator."""

    def test_valid_config(self):
        """Test valid DATA.SOURCE config."""
        config = {
            "TYPE": "simulator",
            "CONFIG": {
                "PATH": "/path/to/data.csv",
                "START_DATE": "2024-01-01",
                "END_DATE": "2024-01-31",
            },
        }
        validator = DataSourceValidator()
        errors = validator.validate(config)
        assert len(errors) == 0

    def test_missing_type(self):
        """Test missing TYPE field."""
        config = {
            "CONFIG": {
                "PATH": "/path/to/data.csv",
                "START_DATE": "2024-01-01",
                "END_DATE": "2024-01-31",
            }
        }
        validator = DataSourceValidator()
        errors = validator.validate(config)
        assert any(e.field == "TYPE" for e in errors)

    def test_missing_config(self):
        """Test missing CONFIG field."""
        config = {"TYPE": "simulator"}
        validator = DataSourceValidator()
        errors = validator.validate(config)
        assert any(e.field == "CONFIG" for e in errors)

    def test_missing_path(self):
        """Test missing PATH field."""
        config = {
            "TYPE": "simulator",
            "CONFIG": {
                "START_DATE": "2024-01-01",
                "END_DATE": "2024-01-31",
            },
        }
        validator = DataSourceValidator()
        errors = validator.validate(config)
        assert any(e.field == "PATH" for e in errors)

    def test_invalid_date_format(self):
        """Test invalid date format."""
        config = {
            "TYPE": "simulator",
            "CONFIG": {
                "PATH": "/path/to/data.csv",
                "START_DATE": "01-01-2024",
                "END_DATE": "2024-01-31",
            },
        }
        validator = DataSourceValidator()
        errors = validator.validate(config)
        assert any(e.field == "START_DATE" and "Invalid date format" in e.message for e in errors)

    def test_start_after_end(self):
        """Test START_DATE after END_DATE."""
        config = {
            "TYPE": "simulator",
            "CONFIG": {
                "PATH": "/path/to/data.csv",
                "START_DATE": "2024-01-31",
                "END_DATE": "2024-01-01",
            },
        }
        validator = DataSourceValidator()
        errors = validator.validate(config)
        assert any("Must be before or equal to END_DATE" in e.message for e in errors)


class TestTransformValidator:
    """Tests for TransformValidator."""

    def test_valid_config(self):
        """Test valid TRANSFORM config."""
        config = {"FUNCTION": "aggregate_by_date", "PARAMS": {"metric": "revenue"}}
        validator = TransformValidator()
        errors = validator.validate(config)
        assert len(errors) == 0

    def test_missing_function(self):
        """Test missing FUNCTION field."""
        config = {"PARAMS": {"metric": "revenue"}}
        validator = TransformValidator()
        errors = validator.validate(config)
        assert any(e.field == "FUNCTION" for e in errors)


class TestMeasurementValidator:
    """Tests for MeasurementValidator."""

    def test_valid_its_config(self):
        """Test valid MEASUREMENT config for ITS model."""
        config = {
            "MODEL": "interrupted_time_series",
            "PARAMS": {"intervention_date": "2024-01-15"},
        }
        validator = MeasurementValidator()
        errors = validator.validate(config)
        assert len(errors) == 0

    def test_valid_metrics_approx_config(self):
        """Test valid MEASUREMENT config for metrics_approximation model."""
        config = {
            "MODEL": "metrics_approximation",
            "PARAMS": {},
        }
        validator = MeasurementValidator()
        errors = validator.validate(config)
        assert len(errors) == 0

    def test_missing_model(self):
        """Test missing MODEL field."""
        config = {"PARAMS": {"intervention_date": "2024-01-15"}}
        validator = MeasurementValidator()
        errors = validator.validate(config)
        assert any(e.field == "MODEL" for e in errors)

    def test_missing_params(self):
        """Test missing PARAMS field."""
        config = {"MODEL": "interrupted_time_series"}
        validator = MeasurementValidator()
        errors = validator.validate(config)
        assert any(e.field == "PARAMS" for e in errors)

    def test_its_missing_intervention_date(self):
        """Test ITS model with missing intervention_date."""
        config = {
            "MODEL": "interrupted_time_series",
            "PARAMS": {},
        }
        validator = MeasurementValidator()
        errors = validator.validate(config)
        assert any(e.field == "intervention_date" for e in errors)

    def test_its_invalid_intervention_date(self):
        """Test ITS model with invalid intervention_date format."""
        config = {
            "MODEL": "interrupted_time_series",
            "PARAMS": {"intervention_date": "invalid-date"},
        }
        validator = MeasurementValidator()
        errors = validator.validate(config)
        assert any(e.field == "intervention_date" and "Invalid date format" in e.message for e in errors)


class TestITSParamsValidator:
    """Tests for ITSParamsValidator."""

    def test_valid_params(self):
        """Test valid ITS params."""
        config = {"intervention_date": "2024-01-15"}
        validator = ITSParamsValidator()
        errors = validator.validate(config)
        assert len(errors) == 0

    def test_missing_intervention_date(self):
        """Test missing intervention_date."""
        validator = ITSParamsValidator()
        errors = validator.validate({})
        assert any(e.field == "intervention_date" for e in errors)


class TestMetricsApproximationParamsValidator:
    """Tests for MetricsApproximationParamsValidator."""

    def test_empty_params_valid(self):
        """Test that empty params are valid for metrics_approximation."""
        validator = MetricsApproximationParamsValidator()
        errors = validator.validate({})
        assert len(errors) == 0


class TestValidateConfigWithValidators:
    """Tests for the main validation function."""

    def test_valid_full_config(self):
        """Test valid full configuration."""
        config = {
            "DATA": {
                "SOURCE": {
                    "TYPE": "simulator",
                    "CONFIG": {
                        "PATH": "/path/to/data.csv",
                        "START_DATE": "2024-01-01",
                        "END_DATE": "2024-01-31",
                    },
                },
                "TRANSFORM": {"FUNCTION": "aggregate_by_date", "PARAMS": {}},
            },
            "MEASUREMENT": {
                "MODEL": "interrupted_time_series",
                "PARAMS": {"intervention_date": "2024-01-15"},
            },
        }
        errors = validate_config_with_validators(config)
        assert len(errors) == 0

    def test_missing_data_section(self):
        """Test missing DATA section."""
        config = {
            "MEASUREMENT": {
                "MODEL": "interrupted_time_series",
                "PARAMS": {"intervention_date": "2024-01-15"},
            }
        }
        errors = validate_config_with_validators(config)
        assert any(e.field == "DATA" for e in errors)

    def test_missing_measurement_section(self):
        """Test missing MEASUREMENT section."""
        config = {
            "DATA": {
                "SOURCE": {
                    "TYPE": "simulator",
                    "CONFIG": {
                        "PATH": "/path/to/data.csv",
                        "START_DATE": "2024-01-01",
                        "END_DATE": "2024-01-31",
                    },
                }
            }
        }
        errors = validate_config_with_validators(config)
        assert any(e.field == "MEASUREMENT" for e in errors)

    def test_missing_source_in_data(self):
        """Test missing SOURCE in DATA."""
        config = {
            "DATA": {"TRANSFORM": {"FUNCTION": "aggregate_by_date"}},
            "MEASUREMENT": {
                "MODEL": "interrupted_time_series",
                "PARAMS": {"intervention_date": "2024-01-15"},
            },
        }
        errors = validate_config_with_validators(config)
        assert any(e.field == "SOURCE" and e.section == "DATA" for e in errors)

    def test_transform_validated_when_present(self):
        """Test TRANSFORM is validated when present."""
        config = {
            "DATA": {
                "SOURCE": {
                    "TYPE": "simulator",
                    "CONFIG": {
                        "PATH": "/path/to/data.csv",
                        "START_DATE": "2024-01-01",
                        "END_DATE": "2024-01-31",
                    },
                },
                "TRANSFORM": {"PARAMS": {}},  # Missing FUNCTION
            },
            "MEASUREMENT": {
                "MODEL": "interrupted_time_series",
                "PARAMS": {"intervention_date": "2024-01-15"},
            },
        }
        errors = validate_config_with_validators(config)
        assert any(e.field == "FUNCTION" for e in errors)

    def test_multiple_errors_collected(self):
        """Test that multiple errors are collected."""
        config = {
            "DATA": {
                "SOURCE": {
                    "TYPE": "simulator",
                    "CONFIG": {
                        # Missing PATH
                        "START_DATE": "invalid-date",
                        "END_DATE": "2024-01-31",
                    },
                }
            },
            "MEASUREMENT": {
                "MODEL": "interrupted_time_series",
                "PARAMS": {},  # Missing intervention_date
            },
        }
        errors = validate_config_with_validators(config)
        # Should have at least: missing PATH, invalid START_DATE, missing intervention_date
        assert len(errors) >= 3


class TestConfigValidatorIntegrationWithParser:
    """Tests for integration with ConfigurationParser."""

    def test_parser_uses_pluggable_validators(self):
        """Test that ConfigurationParser uses pluggable validators by default."""
        import json
        import tempfile
        from pathlib import Path

        import pandas as pd

        from impact_engine.config import ConfigurationParser

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create products file
            products_path = str(Path(tmpdir) / "products.csv")
            pd.DataFrame({"product_id": ["p1"]}).to_csv(products_path, index=False)

            # Create valid config
            config = {
                "DATA": {
                    "SOURCE": {
                        "TYPE": "simulator",
                        "CONFIG": {
                            "PATH": products_path,
                            "START_DATE": "2024-01-01",
                            "END_DATE": "2024-01-31",
                        },
                    }
                },
                "MEASUREMENT": {
                    "MODEL": "interrupted_time_series",
                    "PARAMS": {"intervention_date": "2024-01-15"},
                },
            }

            config_path = str(Path(tmpdir) / "config.json")
            with open(config_path, "w") as f:
                json.dump(config, f)

            parser = ConfigurationParser()
            result = parser.parse_config(config_path)

            assert result["DATA"]["SOURCE"]["TYPE"] == "simulator"

    def test_parser_uses_legacy_validation_when_specified(self):
        """Test that parser can use legacy validation."""
        import json
        import tempfile
        from pathlib import Path

        import pandas as pd

        from impact_engine.config import ConfigurationParser

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create products file
            products_path = str(Path(tmpdir) / "products.csv")
            pd.DataFrame({"product_id": ["p1"]}).to_csv(products_path, index=False)

            # Create valid config
            config = {
                "DATA": {
                    "SOURCE": {
                        "TYPE": "simulator",
                        "CONFIG": {
                            "PATH": products_path,
                            "START_DATE": "2024-01-01",
                            "END_DATE": "2024-01-31",
                        },
                    }
                },
                "MEASUREMENT": {
                    "MODEL": "interrupted_time_series",
                    "PARAMS": {"intervention_date": "2024-01-15"},
                },
            }

            config_path = str(Path(tmpdir) / "config.json")
            with open(config_path, "w") as f:
                json.dump(config, f)

            parser = ConfigurationParser(use_legacy_validation=True)
            result = parser.parse_config(config_path)

            assert result["DATA"]["SOURCE"]["TYPE"] == "simulator"
