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
    import asyncio

    logger = structlog.get_logger("lifespan")

    # 1. Initialize Database Connection
    database = container.resolve('database')
    logger.info("Initializing database connection...")
    await database.connect()

    # 1.1 Setup WebSocket Connection Manager Dependencies
    from app.edge.socket.connection_manager import manager
    from app.di.container import container
    
    prometheus = container.resolve('prometheus')
    redis = container.resolve('cache')
    manager.set_dependencies(prometheus=prometheus, redis=redis)
    await manager.start()

    # 2. Initialize Models (create tables) - controlled by setting
    if settings.DB_AUTO_MIGRATE:
        logger.info("Initializing models (DB_AUTO_MIGRATE=True)...")
        await initialize_models(database)
    else:
        logger.info("Skipping model initialization (DB_AUTO_MIGRATE=False)")

    # 3. Connect RabbitMQ and start consumers
    rabbitmq = container.resolve('rabbitmq')
    logger.info("Connecting to RabbitMQ...")
    await rabbitmq.connect()

    from app.workers.ai_message_consumer import start_ai_message_consumer
    from app.workers.knowledge_consumer import start_knowledge_consumer

    # Start both consumers as background tasks (non-blocking)
    asyncio.create_task(start_ai_message_consumer(rabbitmq))
    asyncio.create_task(start_knowledge_consumer(rabbitmq))
    logger.info("✓ RabbitMQ consumers started")

    logger.info("✓ Application startup complete")

    yield

    # 4. Shutdown logic
    logger.info("Shutting down application...")
    await manager.stop()
    await rabbitmq.disconnect()
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
    
    # Setup WebSocket routes
    from app.edge.socket.socket_route import register_socket_routes
    register_socket_routes(app)
    
    # Setup Prometheus metrics
    from app.di.container import container
    prometheus = container.resolve('prometheus')
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
