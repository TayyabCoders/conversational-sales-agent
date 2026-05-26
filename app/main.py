"""
Main FastAPI application entry point
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.configs.app_config import settings
from app.configs.logger_config import setup_logging

from app.di import load_all_dependencies
from app.edge.http.routes import register_routes


from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle application startup and shutdown events.
    """
    from app.di.container import container
    from app.models import initialize_models
    import structlog
    
    logger = structlog.get_logger("lifespan")
    
    # 1. Initialize Database Connection
    database = container.resolve('database')
    logger.info("Initializing database connection...")
    await database.connect()
    
    # 1.1 Start WebSocket Connection Manager Background Tasks
    from app.edge.socket.connection_manager import manager
    await manager.start()
    
    # 2. Initialize Models (create tables) - controlled by setting
    if settings.DB_AUTO_MIGRATE:
        logger.info("Initializing models (DB_AUTO_MIGRATE=True)...")
        await initialize_models(database)
    else:
        logger.info("Skipping model initialization (DB_AUTO_MIGRATE=False)")
    
    logger.info("✓ Application startup complete")
    
    yield
    
    # 3. Shutdown logic
    logger.info("Shutting down application...")
    await manager.stop()
    await database.disconnect()
    logger.info("✓ Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    # Initialize logging
    setup_logging()

    load_all_dependencies()
    
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan
    )

    # Register all middlewares
    from app.middlewares import register_middlewares
    register_middlewares(app)

    register_routes(app)
    
    # 6. Setup WebSocket routes
    from app.edge.socket.socket_route import register_socket_routes
    from app.edge.socket.connection_manager import manager
    from app.di.container import container
    
    prometheus = container.resolve('prometheus')
    redis = container.resolve('cache')
    manager.set_dependencies(prometheus=prometheus, redis=redis)
    register_socket_routes(app)
    
    # 5. Setup Prometheus metrics
    prometheus.setup_metrics(app)
    
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
