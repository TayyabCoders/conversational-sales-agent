"""
Dependency loader with explicit order and dynamic loading
"""
import os
from pathlib import Path
from typing import Dict, Any
import importlib
import structlog
from app.di.container import container, Container
from app.configs.app_config import settings

logger = structlog.get_logger(__name__)

# Base directory for app
BASE_DIR = Path(__file__).parent.parent

def should_load_file(file: str) -> bool:
    return (
        file.endswith('.py')
        and not file.startswith(('_', '.'))
        and 'test' not in file.lower()
        and 'spec' not in file.lower()
    )

def get_module_name(file: str) -> str:
    """Extract module name from filename"""
    return file.replace('.py', '').replace('.config', '')

def load_modules_from_directory(directory: str) -> Dict[str, Any]:
    """
    Load modules from a directory
    Registers plain modules (e.g., configs, utils)
    """
    dir_path = BASE_DIR / directory
    modules = {}

    if not dir_path.exists():
        logger.warning(f"Directory not found or inaccessible: {dir_path}")
        return modules

    for file in os.listdir(dir_path):
        if should_load_file(file):
            module_name = get_module_name(file)
            module_path = directory.replace('/', '.')
            full_module_name = f"app.{module_path}.{module_name}"
            try:
                module = importlib.import_module(full_module_name)
                modules[module_name] = module
                logger.debug(f"✓ Loaded {directory}/{module_name}")
            except Exception as e:
                logger.error(f"Failed to load {directory}/{module_name}: {e}")

    return modules

def load_factory_modules(
    directory: str,
    suffix: str,
    singleton: bool = False
) -> Dict[str, Any]:
    """
    Load modules and register classes based on naming convention
    Example: stem 'user' + suffix 'Service' -> class 'UserService' in 'user_service.py'
    """
    singular_suffix = suffix.lower().rstrip('s') if suffix.lower().endswith('s') else suffix.lower()
    registered_modules = {}
    
    dir_path = BASE_DIR / directory
    if not dir_path.is_dir():
        logger.warning(f"Directory not found: {dir_path}")
        return registered_modules

    for file in os.listdir(dir_path):
        if not file.endswith(f"_{singular_suffix}.py"):
            continue

        stem = file[:-len(f"_{singular_suffix}.py")]
        module_path = directory.replace('/', '.')
        full_module_name = f"app.{module_path}.{stem}_{singular_suffix}"

        try:
            module = importlib.import_module(full_module_name)

            # Assume class name convention: UserProfile → UserProfileService / Mediator / etc
            class_name = f"{''.join(w.capitalize() for w in stem.split('_'))}{suffix}"
            cls = getattr(module, class_name, None)

            if cls and isinstance(cls, type):
                reg_name = f"{stem}_{suffix.lower()}"   
                container.register(reg_name, cls, singleton=singleton)
                registered_modules[reg_name] = cls
                logger.debug(f"Registered {reg_name} ({'singleton' if singleton else 'transient'}) ← {class_name}")
            else:
                logger.warning(f"No class '{class_name}' found in {full_module_name}")

        except ImportError as e:
            logger.warning(f"Cannot import {full_module_name}: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error loading {full_module_name}")

    return registered_modules

def load_configurations():
    """Load configuration modules"""
    logger.info('Loading configurations...')
    try:
        configs = load_modules_from_directory('configs')
        container.register_batch(configs, singleton=True)
        logger.info(f"✓ Loaded {len(configs)} configurations")
    except Exception as e:
        logger.error('Failed to load configurations:', exc_info=True)
        raise

def load_utilities():
    """Load utility modules"""
    logger.info('Loading utilities...')
    try:
        utils = load_modules_from_directory('utils')
        container.register_batch(utils, singleton=True)
        logger.info(f"✓ Loaded {len(utils)} utilities")
    except Exception as e:
        logger.error('Failed to load utilities:', exc_info=True)
        raise

def load_models():
    """Load and initialize models"""
    logger.info('Loading models...')
    try:
        models = load_modules_from_directory('models')
        container.register_batch(models, singleton=True)
        logger.info('✓ Loaded models')
    except Exception as e:
        logger.error('Failed to load models:', exc_info=True)
        raise


def load_validators():
    """Load validators"""
    logger.info('Loading validators...')
    try:
        validators = load_modules_from_directory('validators')
        container.register_batch(validators, singleton=True)
        logger.info('✓ Loaded validators')
    except Exception as e:
        logger.error('Failed to load validators:', exc_info=True)
        raise

def load_strategies():
    """Load strategy modules"""
    logger.info('Loading strategies...')
    try:
        strategies = load_factory_modules('strategies', 'Strategy')
        logger.info(f"✓ Loaded {len(strategies)} strategies")
    except Exception as e:
        logger.error('Failed to load strategies:', exc_info=True)
        raise

def load_repositories():
    """Load repository modules"""
    logger.info('Loading repositories...')
    try:
        repos = load_factory_modules('repositories', 'Repository')
        logger.info(f"✓ Loaded {len(repos)} repositories")
    except Exception as e:
        logger.error('Failed to load repositories:', exc_info=True)
        raise

def load_services():
    """Load service modules"""
    logger.info('Loading services...')
    try:
        services = load_factory_modules('services', 'Service')
        logger.info(f"✓ Loaded {len(services)} services")
    except Exception as e:
        logger.error('Failed to load services:', exc_info=True)
        raise

def load_mediators():
    """Load mediator modules"""
    logger.info('Loading mediators...')
    try:            
        mediators = load_factory_modules('mediator', 'Mediator')
        logger.info(f"✓ Loaded {len(mediators)} mediators")
    except Exception as e:
        logger.error('Failed to load mediators:', exc_info=True)
        raise

def load_controllers():
    """Load controller modules"""
    logger.info('Loading controllers...')
    try:
        controllers = load_factory_modules('edge/http/controller', 'Controller', singleton=True)
        logger.info(f"✓ Loaded {len(controllers)} controllers")
    except Exception as e:
        logger.error('Failed to load controllers:', exc_info=True)
        raise

def load_infrastructure():
    """Load infrastructure explicitly"""
    logger.info('Loading infrastructure...')

    try:
        container.config.from_dict(settings.model_dump())

        from app.configs.database_config import Database
        container.register(
            'database',
            lambda: Database(
            master_config={
                "host": settings.DB_MASTER_HOST,
                "port": settings.DB_MASTER_PORT,
                "username": settings.DB_MASTER_USERNAME,
                "password": settings.DB_MASTER_PASSWORD,
                "database": settings.DB_MASTER_DATABASE,
            },
            replica_config={
                "host": settings.DB_REPLICA_HOST,
                "port": settings.DB_REPLICA_PORT,
                "username": settings.DB_REPLICA_USERNAME,
                "password": settings.DB_REPLICA_PASSWORD,
                "database": settings.DB_REPLICA_DATABASE,
            }
        ),
        singleton=True)

        from app.configs.cache_config import RedisCache
        container.register(
            'cache',
            lambda: RedisCache(
                host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            cluster_mode=settings.REDIS_CLUSTER_MODE,
        ),
        singleton=True)


        from app.configs.messaging_config import RabbitMQClient
        container.register(
            'rabbitmq',
            lambda: RabbitMQClient(
                host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            username=settings.RABBITMQ_USERNAME,
            password=settings.RABBITMQ_PASSWORD,
            virtual_host=settings.RABBITMQ_VIRTUAL_HOST,
        ),
        singleton=True)

        from app.configs.messaging_config import KafkaClient
        container.register(
            'kafka',
            lambda: KafkaClient(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                client_id=settings.KAFKA_CLIENT_ID,
                group_id=settings.KAFKA_GROUP_ID,
            ),
            singleton=True
        )

        from app.configs.monitoring_config import PrometheusMetrics
        container.register(
            'prometheus',
            lambda: PrometheusMetrics(
                enabled=settings.PROMETHEUS_ENABLED,
                port=settings.PROMETHEUS_PORT,
            ),
            singleton=True
        )

        logger.info('✓ Infrastructure loaded')

    except Exception as e:
        logger.error('Failed to load infrastructure:', exc_info=True)
        raise

def load_all_dependencies():
    """Main loading function with order"""
    logger.info('Starting dependency loading...')
    try:
        load_infrastructure()
        load_configurations()
        load_utilities()
        load_models()
        load_validators()
        load_strategies()
        load_repositories()
        load_services()
        load_mediators()
        load_controllers()
        
        # Wire the container for auto-wiring across the app package
        # We exclude app.main and app.di to avoid circular imports during loading
        container.wire(
            packages=[
                "app.edge.http.routes",
                "app.edge.http.controller",
                "app.mediator",
                "app.services",
                "app.repositories",
                "app.middlewares",
            ]
        )
        logger.info(f"✓  All dependencies loaded successfully ({container.size()} total)")
        return container
    except Exception as e:
        logger.error('Critical error during dependency loading:', exc_info=True)
        raise

def health_check(container: Container) -> Dict:
    """Health check for container"""
    stats = container.get_stats()
    required_dependencies = ['database', 'cache', 'models']
    missing = [dep for dep in required_dependencies if not container.has(dep)]
    if missing:
        logger.warning(f"Missing critical dependencies: {', '.join(missing)}")
        return {
            'healthy': False,
            'missing': missing,
            'stats': stats
        }
    logger.info('Container health check passed')
    return {
        'healthy': True,
        'missing': [],
        'stats': stats
    }

__all__ = ['load_all_dependencies', 'health_check']