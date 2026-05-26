"""
Main DI module entry point
Loads dependencies and exports public API
"""
from app.di.container import container, get_container, inject, Provide
from app.di.loader import load_all_dependencies, health_check


# Export public API
__all__ = ["container", "get_container", "load_all_dependencies","inject", "Provide", "health_check"]