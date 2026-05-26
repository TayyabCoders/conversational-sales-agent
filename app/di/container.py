"""
Core Dependency Injection Container
"""
from typing import Any, Callable, Dict, Optional, List
from dependency_injector import containers, providers
from dependency_injector.wiring import inject, Provide
import structlog

logger = structlog.get_logger(__name__)

class Container(containers.DynamicContainer):
    """Main application container"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config = providers.Configuration()
        logger.debug("✓ Container initialized")

    def wire(self, packages: Optional[List[str]] = None, modules: Optional[List[Any]] = None):
        """
        Wire the container for atuo-wiring
        """
        super().wire(packages=packages, modules=modules)
        logger.debug(f"✓ Container wired to: {packages or modules}")

    def register(self, name: str, factory: Any, singleton: bool = False):
        """
        Register a dependency with auto-binding of constructor arguments
        """
        if not name or not isinstance(name, str):
            raise ValueError('Dependency name must be a non-empty string')

        # Auto-bind arguments if it's a class
        kwargs = {}
        if isinstance(factory, type):
            import inspect
            try:
                sig = inspect.signature(factory.__init__)
                for param_name in sig.parameters:
                    if param_name != 'self' and self.has(param_name):
                        kwargs[param_name] = getattr(self, param_name)
                        logger.debug(f"  └─ Auto-bound dependency: {param_name}")
            except Exception as e:
                logger.debug(f"  └─ Skipping auto-bind for {name}: {e}")

        if singleton:
            if isinstance(factory, type):
                provider = providers.Singleton(factory, **kwargs)
            elif callable(factory):
                provider = providers.Singleton(factory)
            else:
                provider = providers.Object(factory)
        else:
            if isinstance(factory, type):
                provider = providers.Factory(factory, **kwargs)
            elif callable(factory):
                provider = providers.Factory(factory)
            else:
                provider = providers.Factory(lambda: factory)

        self.set_provider(name, provider)
        logger.debug(f"✓ Registered dependency: {name}{' (singleton)' if singleton else ''}")

    def register_batch(self, deps: Dict[str, Any], singleton: bool = False):
        """
        Register multiple dependencies
        """
        for name, factory in deps.items():
            self.register(name, factory, singleton=singleton)

    def resolve(self, name: str) -> Any:
        """
        Resolve a dependency by name
        """
        if not self.has(name):
            raise ValueError(f"Dependency '{name}' not found. Available: {', '.join(self.list())}")

        provider = getattr(self, name)
        return provider()

    def resolve_all(self) -> Dict[str, Any]:
        """
        Resolve all dependencies
        """
        resolved = {}
        for name in self.list():
            try:
                resolved[name] = self.resolve(name)
            except Exception as e:
                logger.warning(f"Failed to resolve dependency '{name}': {e}")
        return resolved

    def has(self, name: str) -> bool:
        """
        Check if dependency exists
        """
        return hasattr(self, name) and isinstance(getattr(self, name), providers.Provider)

    def list(self) -> List[str]:
        """
        Get list of registered dependency names
        """
        return [attr for attr in dir(self) if self.has(attr)]

    def size(self) -> int:
        """
        Get dependency count
        """
        return len(self.list())

    def remove(self, name: str):
        """
        Remove a dependency
        """
        if self.has(name):
            delattr(self, name)
            logger.debug(f"✓ Removed dependency: {name}")

    def clear(self):
        """
        Clear all dependencies
        """
        count = self.size()
        for name in list(self.list()):
            self.remove(name)
        logger.debug(f"✓ Cleared {count} dependencies")

    def get_stats(self) -> Dict:
        """
        Get container statistics
        """
        return {
            'total_dependencies': self.size(),
            'dependencies': self.list()
        }


# Create global container instance
container = Container()

def get_container() -> Container:
    """Get container instance"""
    return container

# Export wiring decorators
__all__ = ["container", "get_container", "inject", "Provide"]