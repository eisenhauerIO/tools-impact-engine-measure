"""
Generic registries for components.

This module provides reusable Registry classes that handle registration,
lookup, and validation for adapters like models, metrics sources, and functions.
"""

from typing import Callable, Dict, Generic, List, Type, TypeVar

T = TypeVar("T")
F = TypeVar("F", bound=Callable)


class Registry(Generic[T]):
    """Generic registry for class-based components.

    Provides a consistent pattern for registering and retrieving adapters
    by name, with validation against a base class.

    Example:
        MODEL_REGISTRY = Registry(Model, "model")
        MODEL_REGISTRY.register("my_model", MyModelAdapter)
        model = MODEL_REGISTRY.get("my_model")
    """

    def __init__(self, base_class: Type[T], name: str):
        """Initialize the registry.

        Args:
            base_class: The base class/protocol that registered items must implement.
            name: Human-readable name for error messages (e.g., "model", "metrics adapter").
        """
        self._registry: Dict[str, Type[T]] = {}
        self._base = base_class
        self._name = name

    def register(self, key: str, cls: Type[T]) -> None:
        """Register a class under the given key.

        Args:
            key: The identifier to register the class under.
            cls: The class to register (must be a subclass of base_class).

        Raises:
            ValueError: If cls is not a subclass of base_class.
        """
        if not issubclass(cls, self._base):
            raise ValueError(f"{cls.__name__} must implement {self._base.__name__}")
        self._registry[key] = cls

    def get(self, key: str) -> T:
        """Get an instance of the registered class.

        Args:
            key: The identifier to look up.

        Returns:
            A new instance of the registered class.

        Raises:
            ValueError: If the key is not registered.
        """
        if key not in self._registry:
            available = list(self._registry.keys())
            raise ValueError(f"Unknown {self._name} '{key}'. Available: {available}")
        return self._registry[key]()

    def keys(self) -> List[str]:
        """Return all registered keys."""
        return list(self._registry.keys())

    def register_decorator(self, key: str) -> Callable[[Type[T]], Type[T]]:
        """Return a decorator that registers the class under the given key.

        Enables self-registration pattern where adapters register themselves
        at import time, avoiding explicit registration in factory files.

        Example:
            @MODEL_REGISTRY.register_decorator("my_model")
            class MyModelAdapter(Model):
                ...
        """

        def decorator(cls: Type[T]) -> Type[T]:
            self.register(key, cls)
            return cls

        return decorator


class FunctionRegistry(Generic[F]):
    """Generic registry for callable functions.

    Unlike Registry which stores and instantiates classes,
    FunctionRegistry stores and returns callables directly.

    Example:
        TRANSFORM_REGISTRY = FunctionRegistry("transform")
        TRANSFORM_REGISTRY.register("my_transform", my_transform_func)
        transform = TRANSFORM_REGISTRY.get("my_transform")
    """

    def __init__(self, name: str):
        """Initialize the registry.

        Args:
            name: Human-readable name for error messages (e.g., "transform").
        """
        self._registry: Dict[str, F] = {}
        self._name = name

    def register(self, key: str, func: F) -> None:
        """Register a function under the given key.

        Args:
            key: The identifier to register the function under.
            func: The callable to register.

        Raises:
            ValueError: If func is not callable.
        """
        if not callable(func):
            raise ValueError(f"{self._name} must be callable, got {type(func)}")
        self._registry[key] = func

    def get(self, key: str) -> F:
        """Get a registered function by key.

        Args:
            key: The identifier to look up.

        Returns:
            The registered callable.

        Raises:
            ValueError: If the key is not registered.
        """
        if key not in self._registry:
            available = list(self._registry.keys())
            raise ValueError(f"Unknown {self._name} '{key}'. Available: {available}")
        return self._registry[key]

    def keys(self) -> List[str]:
        """Return all registered keys."""
        return list(self._registry.keys())

    def register_decorator(self, key: str) -> Callable[[F], F]:
        """Return a decorator that registers the function under the given key.

        Example:
            @TRANSFORM_REGISTRY.register_decorator("my_transform")
            def my_transform(data, params):
                ...
        """

        def decorator(func: F) -> F:
            self.register(key, func)
            return func

        return decorator
