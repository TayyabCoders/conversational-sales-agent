# Endpoints package
import importlib
import pkgutil
from fastapi import FastAPI

def register_routes(app: FastAPI):
    package_name = __name__  # app.edge.http.routes
    package = importlib.import_module(package_name)

    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        if not module_name.endswith("_route"):
            continue

        module = importlib.import_module(f"{package_name}.{module_name}")

        if not hasattr(module, "router"):
            continue

        prefix = "/" + module_name.replace("_route", "")
        app.include_router(
            module.router,
            prefix=f"/api/v1{prefix}",
            tags=[prefix.strip("/")]
        )
