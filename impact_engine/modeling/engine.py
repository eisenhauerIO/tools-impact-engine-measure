"""
Modeling Engine for coordinating model operations.
"""

import pandas as pd
import logging
import time
from typing import Dict, List, Any, Optional

from .base import ModelInterface
from ..config import ConfigurationParser, ConfigurationError


class ModelingEngine:
    """
    Central coordinator for model management and configuration.
    
    This class provides the main interface for the modeling abstraction layer,
    handling configuration loading, model selection, and coordinating
    model fitting operations across different model implementations.
    
    Supports direct registration of external models via the register_model method.
    """
    
    def __init__(self, enable_debug_logging: bool = False):
        """
        Initialize the ModelingEngine with empty registry and configuration.
        
        Args:
            enable_debug_logging: If True, enables detailed execution traces for debugging
        """
        self.logger = logging.getLogger(__name__)
        self.config_parser = ConfigurationParser()
        self.model_registry: Dict[str, type] = {}
        self.current_config: Optional[Dict[str, Any]] = None
        self.current_model: Optional[ModelInterface] = None
        self.debug_logging = enable_debug_logging
        
        # Performance tracking
        self.operation_stats = {
            'config_loads': 0,
            'model_fits': 0,
            'model_instantiations': 0,
            'total_fit_time': 0.0,
            'failed_operations': 0
        }
        
        if self.debug_logging:
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug("ModelingEngine initialized with debug logging enabled")
    
    def register_model(self, model_type: str, model_class: type) -> None:
        """
        Register a new model implementation for dynamic registration.
        
        This is the main API for external model registration. Users can
        create their own model implementations and register them here.
        
        Args:
            model_type: String identifier for the model type (e.g., "interrupted_time_series", "causal_impact")
            model_class: Class implementing ModelInterface
        
        Raises:
            ValueError: If model_class doesn't implement ModelInterface
        
        Example:
            # External model registration
            from my_package.causal_impact import CausalImpactModel
            
            engine = ModelingEngine()
            engine.register_model("causal_impact", CausalImpactModel)
            
            # Now can use "causal_impact" as model type in configuration
        """
        try:
            if self.debug_logging:
                self.logger.debug(f"Attempting to register model type '{model_type}' with class {model_class.__name__}")
            
            if not issubclass(model_class, ModelInterface):
                error_msg = f"Model class {model_class.__name__} must implement ModelInterface"
                self.logger.error(f"Registration failed for '{model_type}': {error_msg}")
                raise ValueError(error_msg)
            
            self.model_registry[model_type] = model_class
            self.logger.info(f"Successfully registered model type '{model_type}' with class {model_class.__name__}")
            
            if self.debug_logging:
                self.logger.debug(f"Registry now contains {len(self.model_registry)} model types: {list(self.model_registry.keys())}")
                
        except Exception as e:
            self.logger.error(f"Unexpected error during model registration for '{model_type}': {e}")
            self.operation_stats['failed_operations'] += 1
            raise
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load and validate configuration from file.
        
        Args:
            config_path: Path to the configuration file (JSON or YAML)
        
        Returns:
            Dict[str, Any]: Parsed and validated configuration
        
        Raises:
            ConfigurationError: If configuration parsing or validation fails
            FileNotFoundError: If configuration file does not exist
        """
        start_time = time.time()
        
        try:
            if self.debug_logging:
                self.logger.debug(f"Starting configuration load from {config_path}")
            
            self.current_config = self.config_parser.parse_config(config_path)
            
            load_time = time.time() - start_time
            self.operation_stats['config_loads'] += 1
            
            self.logger.info(f"Successfully loaded configuration from {config_path} in {load_time:.3f}s")
            
            if self.debug_logging:
                measurement = self.current_config.get('MEASUREMENT', {})
                self.logger.debug(f"Configuration contains model type: {measurement.get('MODEL', 'unknown')}")
                self.logger.debug(f"Model parameters: {measurement.get('PARAMS', {})}")
            
            return self.current_config
            
        except FileNotFoundError as e:
            load_time = time.time() - start_time
            self.operation_stats['failed_operations'] += 1
            error_msg = f"Configuration file not found: {config_path}"
            self.logger.error(f"{error_msg} (failed after {load_time:.3f}s)")
            raise FileNotFoundError(error_msg) from e
            
        except ConfigurationError as e:
            load_time = time.time() - start_time
            self.operation_stats['failed_operations'] += 1
            error_msg = f"Configuration validation failed for {config_path}: {e}"
            self.logger.error(f"{error_msg} (failed after {load_time:.3f}s)")
            raise ConfigurationError(error_msg) from e
            
        except Exception as e:
            load_time = time.time() - start_time
            self.operation_stats['failed_operations'] += 1
            error_msg = f"Unexpected error loading configuration from {config_path}: {e}"
            self.logger.error(f"{error_msg} (failed after {load_time:.3f}s)")
            raise ConfigurationError(error_msg) from e
    
    def get_model(self, model_type: Optional[str] = None) -> ModelInterface:
        """
        Get model implementation based on configuration or specified type.
        
        Args:
            model_type: Optional model type. If None, uses current config.
        
        Returns:
            ModelInterface: Instance of the appropriate model implementation
        
        Raises:
            ValueError: If model_type is not registered or configuration is missing
            ConfigurationError: If no configuration is loaded and model_type is None
        """
        start_time = time.time()
        
        try:
            if self.debug_logging:
                self.logger.debug(f"Getting model for type: {model_type}")
            
            if model_type is None:
                if self.current_config is None:
                    error_msg = "No configuration loaded. Call load_config() first or provide model_type."
                    self.logger.error(error_msg)
                    raise ConfigurationError(error_msg)
                model_type = self.current_config["MEASUREMENT"]["MODEL"]
                
                if self.debug_logging:
                    self.logger.debug(f"Using model type from config: {model_type}")
            
            if model_type not in self.model_registry:
                available_types = list(self.model_registry.keys())
                error_msg = f"Unknown model type '{model_type}'. Available types: {available_types}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Create new instance of the model
            model_class = self.model_registry[model_type]
            
            if self.debug_logging:
                self.logger.debug(f"Creating instance of {model_class.__name__}")
            
            self.operation_stats['model_instantiations'] += 1
            model = model_class()
            
            total_time = time.time() - start_time
            
            if self.debug_logging:
                self.logger.debug(f"Model creation completed in {total_time:.3f}s")
            
            return model
            
        except Exception as e:
            total_time = time.time() - start_time
            self.operation_stats['failed_operations'] += 1
            self.logger.error(f"Failed to get model (took {total_time:.3f}s): {e}")
            raise
    
    def fit_model(
        self,
        data: pd.DataFrame,
        intervention_date: str,
        output_path: str,
        model_type: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Fit a model to the provided data and save results.
        
        Args:
            data: DataFrame containing time series data with required columns.
                  Must include 'date' column and dependent variable column.
            intervention_date: Date string (YYYY-MM-DD format) indicating when
                             the intervention occurred.
            output_path: Directory path where model results should be saved.
            model_type: Optional model type. If None, uses current config.
            **kwargs: Additional model-specific parameters.
        
        Returns:
            str: Path to the saved results file.
        
        Raises:
            ValueError: If data validation fails or model_type is not registered
            ConfigurationError: If no configuration is loaded and model_type is None
            RuntimeError: If model fitting fails
        """
        start_time = time.time()
        
        try:
            if self.debug_logging:
                self.logger.debug(f"Starting model fitting with intervention date: {intervention_date}")
            
            # Input validation
            if data.empty:
                error_msg = "Input data cannot be empty"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            
            if self.debug_logging:
                self.logger.debug(f"Input data shape: {data.shape}")
                self.logger.debug(f"Data columns: {list(data.columns)}")
            
            # Get model instance
            model = self.get_model(model_type)
            
            # Validate data before fitting
            validation_start = time.time()
            if not model.validate_data(data):
                validation_time = time.time() - validation_start
                error_msg = f"Data validation failed for model {model.__class__.__name__}"
                self.logger.error(f"{error_msg} (validation took {validation_time:.3f}s)")
                self.operation_stats['failed_operations'] += 1
                raise ValueError(error_msg)
            
            validation_time = time.time() - validation_start
            if self.debug_logging:
                self.logger.debug(f"Data validation passed in {validation_time:.3f}s")
            
            # Fit the model
            fit_start = time.time()
            self.operation_stats['model_fits'] += 1
            
            if self.debug_logging:
                self.logger.debug(f"Calling fit method on {model.__class__.__name__}")
            
            result_path = model.fit(
                data=data,
                intervention_date=intervention_date,
                output_path=output_path,
                **kwargs
            )
            
            fit_time = time.time() - fit_start
            total_time = time.time() - start_time
            
            self.operation_stats['total_fit_time'] += fit_time
            
            self.logger.info(
                f"Successfully fitted {model.__class__.__name__} model "
                f"in {total_time:.3f}s (fit: {fit_time:.3f}s). "
                f"Results saved to {result_path}"
            )
            
            if self.debug_logging:
                self.logger.debug(f"Model fit completed. Result path: {result_path}")
            
            return result_path
            
        except ValueError as e:
            total_time = time.time() - start_time
            self.operation_stats['failed_operations'] += 1
            self.logger.error(f"Input validation error (after {total_time:.3f}s): {e}")
            raise
            
        except ConfigurationError as e:
            total_time = time.time() - start_time
            self.operation_stats['failed_operations'] += 1
            self.logger.error(f"Configuration error (after {total_time:.3f}s): {e}")
            raise
            
        except Exception as e:
            total_time = time.time() - start_time
            self.operation_stats['failed_operations'] += 1
            error_msg = f"Unexpected error during model fitting (after {total_time:.3f}s): {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available model types.
        
        Returns:
            List[str]: List of registered model type identifiers
        """
        return list(self.model_registry.keys())
    
    def get_current_config(self) -> Optional[Dict[str, Any]]:
        """
        Get the currently loaded configuration.
        
        Returns:
            Optional[Dict[str, Any]]: Current configuration or None if not loaded
        """
        return self.current_config
    
    def get_operation_stats(self) -> Dict[str, Any]:
        """
        Get performance and operation statistics.
        
        Returns:
            Dict[str, Any]: Dictionary containing operation statistics
        """
        stats = self.operation_stats.copy()
        
        # Calculate derived metrics
        if stats['model_fits'] > 0:
            stats['avg_fit_time'] = stats['total_fit_time'] / stats['model_fits']
        else:
            stats['avg_fit_time'] = 0.0
        
        return stats
    
    def reset_stats(self) -> None:
        """Reset operation statistics."""
        self.operation_stats = {
            'config_loads': 0,
            'model_fits': 0,
            'model_instantiations': 0,
            'total_fit_time': 0.0,
            'failed_operations': 0
        }
        self.logger.info("Operation statistics reset")
    
    def enable_debug_logging(self) -> None:
        """Enable debug logging for detailed execution traces."""
        self.debug_logging = True
        self.logger.setLevel(logging.DEBUG)
        self.logger.debug("Debug logging enabled")
    
    def disable_debug_logging(self) -> None:
        """Disable debug logging."""
        self.debug_logging = False
        self.logger.setLevel(logging.INFO)
        self.logger.info("Debug logging disabled")
