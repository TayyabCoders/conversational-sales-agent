"""
Health check endpoints for monitoring
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends
from dependency_injector.wiring import inject, Provide

from app.di.container import container

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Basic health check"""
    return {"status": "healthy"}


@router.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """Liveness probe for Kubernetes"""
    return {"status": "alive"}


@router.get("/health/ready")
@inject
async def readiness_check(
    container=Depends(Provide[container])
) -> Dict[str, Any]:
    """Readiness probe for Kubernetes with dependency checks"""
    health_status = {
        "status": "ready",
        "timestamp": "2024-01-01T00:00:00Z",  # TODO: Use actual timestamp
        "dependencies": {}
    }
    
    try:
        # Check database health
        db_health = container.database().health_check()
        health_status["dependencies"]["database"] = db_health
        
        # Check cache health
        cache_health = container.cache().health_check()
        health_status["dependencies"]["cache"] = cache_health
        
        # Check RabbitMQ health
        rabbitmq_health = container.rabbitmq().health_check()
        health_status["dependencies"]["rabbitmq"] = rabbitmq_health
        
        # Check Kafka health
        kafka_health = container.kafka().health_check()
        health_status["dependencies"]["kafka"] = kafka_health
        
        # Check Prometheus health
        prometheus_health = container.prometheus().health_check()
        health_status["dependencies"]["prometheus"] = prometheus_health
        
        # Overall status based on dependencies
        all_healthy = all(
            dep.get("status") == "healthy" 
            for dep in health_status["dependencies"].values()
        )
        
        health_status["status"] = "ready" if all_healthy else "not_ready"
        
    except Exception as e:
        health_status["status"] = "error"
        health_status["error"] = str(e)
    
    return health_status


@router.get("/health/detailed")
@inject
async def detailed_health_check(
    container=Depends(Provide[container])
) -> Dict[str, Any]:
    """Detailed health check with all system information"""
    try:
        return {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",  # TODO: Use actual timestamp
            "version": "0.1.0",
            "dependencies": {
                "database": container.database().health_check(),
                "cache": container.cache().health_check(),
                "rabbitmq": container.rabbitmq().health_check(),
                "kafka": container.kafka().health_check(),
                "prometheus": container.prometheus().health_check(),
            },
            "system": {
                "python_version": "3.9+",
                "fastapi_version": "0.104.1",
                "environment": "development",  # TODO: Get from config
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": "2024-01-01T00:00:00Z"
        }
