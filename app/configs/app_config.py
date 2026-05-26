"""
Application configuration using Pydantic settings
"""
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_TITLE: str = "FastAPI Boiler Plate"
    APP_DESCRIPTION: str = "Enterprise FastAPI application with clean architecture"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="console", env="LOG_FORMAT")  # "json" (production) or "console" (dev)
    LOG_OUTPUT: str = Field(default="stdout", env="LOG_OUTPUT")  # "stdout", "file", "both"
    LOG_FILE_PATH: str = Field(default="logs/app.log", env="LOG_FILE_PATH")
    LOG_FILE_MAX_BYTES: int = Field(default=10_485_760, env="LOG_FILE_MAX_BYTES")  # 10MB
    LOG_FILE_BACKUP_COUNT: int = Field(default=5, env="LOG_FILE_BACKUP_COUNT")
    LOG_REDACT_ENABLED: bool = Field(default=True, env="LOG_REDACT_ENABLED")
    LOG_SLOW_REQUEST_THRESHOLD_MS: int = Field(default=500, env="LOG_SLOW_REQUEST_THRESHOLD_MS")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    # Security
    SECRET_KEY: str = Field(env="SECRET_KEY")
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # seconds
    RATE_LIMIT_STORAGE_URL: str = Field(default="memory://", env="RATE_LIMIT_STORAGE_URL")
    RATE_LIMIT_EXEMPT_ROUTES: List[str] = Field(
        default=["/", "/health", "/metrics", "/docs", "/redoc", "/openapi.json"],
        env="RATE_LIMIT_EXEMPT_ROUTES"
    )
    RATE_LIMIT_STRATEGY: str = Field(default="moving-window", env="RATE_LIMIT_STRATEGY")
    RATE_LIMIT_HEADER_ENABLED: bool = Field(default=True, env="RATE_LIMIT_HEADER_ENABLED")
    RATE_LIMIT_TRUST_PROXY: bool = Field(default=True, env="RATE_LIMIT_TRUST_PROXY")
    RATE_LIMIT_KEY_PREFIX: str = Field(default="rate_limit", env="RATE_LIMIT_KEY_PREFIX")

    
    # Database - Primary (Master)
    DB_MASTER_HOST: str = Field(default="localhost", env="DB_MASTER_HOST")
    DB_MASTER_PORT: int = Field(default=5433, env="DB_MASTER_PORT")
    DB_MASTER_USERNAME: str = Field(default="user", env="DB_MASTER_USERNAME")
    DB_MASTER_PASSWORD: str = Field(default="1234", env="DB_MASTER_PASSWORD")
    DB_MASTER_DATABASE: str = Field(default="app_db", env="DB_MASTER_DATABASE")
    
    # Database - Secondary (Replica) - Optional
    DB_REPLICA_HOST: Optional[str] = Field(default=None, env="DB_REPLICA_HOST")
    DB_REPLICA_PORT: Optional[int] = Field(default=None, env="DB_REPLICA_PORT")
    DB_REPLICA_USERNAME: Optional[str] = Field(default=None, env="DB_REPLICA_USERNAME")
    DB_REPLICA_PASSWORD: Optional[str] = Field(default=None, env="DB_REPLICA_PASSWORD")
    DB_REPLICA_DATABASE: Optional[str] = Field(default=None, env="DB_REPLICA_DATABASE")
    # Database schema sync / auto-migration toggle
    DB_AUTO_MIGRATE: bool = Field(default=True, env="DB_AUTO_MIGRATE")
    
    # Redis
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=7004, env="REDIS_PORT")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    REDIS_CLUSTER_MODE: bool = Field(default=False, env="REDIS_CLUSTER_MODE")
    
    # RabbitMQ
    RABBITMQ_HOST: str = Field(default="localhost", env="RABBITMQ_HOST")
    RABBITMQ_PORT: int = Field(default=5673, env="RABBITMQ_PORT")
    RABBITMQ_USERNAME: str = Field(default="admin", env="RABBITMQ_USERNAME")
    RABBITMQ_PASSWORD: str = Field(default="admin", env="RABBITMQ_PASSWORD")
    RABBITMQ_VIRTUAL_HOST: str = Field(default="/", env="RABBITMQ_VIRTUAL_HOST")
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: List[str] = Field(default=["localhost:9093"], env="KAFKA_BOOTSTRAP_SERVERS")
    KAFKA_CLIENT_ID: str = Field(default="fastapi-app", env="KAFKA_CLIENT_ID")
    KAFKA_GROUP_ID: str = Field(default="fastapi-group", env="KAFKA_GROUP_ID")
    
    # Prometheus
    PROMETHEUS_ENABLED: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    PROMETHEUS_PORT: int = Field(default=9091, env="PROMETHEUS_PORT")
    
    # Metrics
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()
