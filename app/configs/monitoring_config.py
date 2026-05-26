"""
Prometheus monitoring infrastructure
"""
from typing import Dict, Any, Optional
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from fastapi import FastAPI, Request, Response
from structlog import get_logger

logger = get_logger(__name__)


class PrometheusMetrics:
    """Prometheus metrics manager"""
    
    def __init__(self, enabled: bool = True, port: int = 9090):
        self.enabled = enabled
        self.port = port
        
        # Use a dedicated registry for custom application metrics to avoid
        # clashing with the global default registry used by other components.
        self.registry = CollectorRegistry()
        
        # Custom metrics (non-HTTP: HTTP metrics are provided by Instrumentator)
        self.active_connections = Gauge(
            "active_connections",
            "Number of active connections",
            registry=self.registry,
        )
        
        self.database_queries = Counter(
            "database_queries_total",
            "Total database queries",
            ["operation", "table", "status"],
            registry=self.registry,
        )
        
        self.database_query_duration = Histogram(
            "database_query_duration_seconds",
            "Database query duration in seconds",
            ["operation", "table"],
            registry=self.registry,
        )
        
        self.cache_hits = Counter(
            "cache_hits_total",
            "Total cache hits",
            registry=self.registry,
        )
        
        self.cache_misses = Counter(
            "cache_misses_total",
            "Total cache misses",
            registry=self.registry,
        )
        
        self.message_published = Counter(
            "messages_published_total",
            "Total messages published",
            ["queue_type", "topic"],
            registry=self.registry,
        )
        
        self.message_consumed = Counter(
            "messages_consumed_total",
            "Total messages consumed",
            ["queue_type", "topic"],
            registry=self.registry,
        )
        
        self.business_events = Counter(
            "business_events_total",
            "Total business events",
            ["event_type", "status"],
            registry=self.registry,
        )
    
    def setup_metrics(self, app: FastAPI) -> None:
        """Setup Prometheus metrics for FastAPI application"""
        if not self.enabled:
            logger.info("Prometheus metrics disabled")
            return
        
        try:
            logger.info("Setting up Prometheus metrics...")
            
            # Setup FastAPI instrumentator
            instrumentator = Instrumentator(
                should_group_status_codes=False,
                should_ignore_untemplated=True,
                should_respect_env_var=True,
                should_instrument_requests_inprogress=True,
                excluded_handlers=["/metrics", "/health"],
                env_var_name="ENABLE_METRICS",
            )
            
            # Add custom metrics
            instrumentator.add(
                metrics.request_size(
                    should_include_handler=True,
                    should_include_method=True,
                    should_include_status=True,
                )
            )
            
            instrumentator.add(
                metrics.response_size(
                    should_include_handler=True,
                    should_include_method=True,
                    should_include_status=True,
                )
            )
            
            instrumentator.add(
                metrics.latency(
                    should_include_handler=True,
                    should_include_method=True,
                    should_include_status=True,
                )
            )
            
            # Instrument the app and expose default /metrics with HTTP metrics
            instrumentator.instrument(app).expose(app)
            
            # Add separate endpoint for custom application metrics using
            # this class's dedicated registry to avoid duplicate series.
            @app.get("/custom-metrics")
            async def custom_metrics_endpoint():
                return Response(
                    content=generate_latest(self.registry),
                    media_type=CONTENT_TYPE_LATEST,
                )
            
            logger.info("Prometheus metrics setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup Prometheus metrics: {e}")
            raise
    
    def record_request(self, method: str, endpoint: str, status: int, duration: float) -> None:
        """Record HTTP request metrics.

        HTTP metrics are handled by prometheus_fastapi_instrumentator; this is kept
        for API compatibility and can be extended if needed without registering
        additional Prometheus time series.
        """
        if not self.enabled:
            return
    
    def record_database_query(
        self,
        operation: str,
        table: str,
        status: str,
        duration: float
    ) -> None:
        """Record database query metrics"""
        if not self.enabled:
            return
        
        try:
            self.database_queries.labels(
                operation=operation,
                table=table,
                status=status
            ).inc()
            
            self.database_query_duration.labels(
                operation=operation,
                table=table
            ).observe(duration)
        except Exception as e:
            logger.error(f"Failed to record database metrics: {e}")
    
    def record_cache_access(self, hit: bool) -> None:
        """Record cache access metrics"""
        if not self.enabled:
            return
        
        try:
            if hit:
                self.cache_hits.inc()
            else:
                self.cache_misses.inc()
        except Exception as e:
            logger.error(f"Failed to record cache metrics: {e}")
    
    def record_message_published(self, queue_type: str, topic: str) -> None:
        """Record message published metrics"""
        if not self.enabled:
            return
        
        try:
            self.message_published.labels(
                queue_type=queue_type,
                topic=topic
            ).inc()
        except Exception as e:
            logger.error(f"Failed to record message published metrics: {e}")
    
    def record_message_consumed(self, queue_type: str, topic: str) -> None:
        """Record message consumed metrics"""
        if not self.enabled:
            return
        
        try:
            self.message_consumed.labels(
                queue_type=queue_type,
                topic=topic
            ).inc()
        except Exception as e:
            logger.error(f"Failed to record message consumed metrics: {e}")
    
    def record_business_event(self, event_type: str, status: str) -> None:
        """Record business event metrics"""
        if not self.enabled:
            return
        
        try:
            self.business_events.labels(
                event_type=event_type,
                status=status
            ).inc()
        except Exception as e:
            logger.error(f"Failed to record business event metrics: {e}")
    
    def set_active_connections(self, count: int) -> None:
        """Set active connections gauge"""
        if not self.enabled:
            return
        
        try:
            self.active_connections.set(count)
        except Exception as e:
            logger.error(f"Failed to set active connections: {e}")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        if not self.enabled:
            return {"status": "disabled"}
        
        try:
            return {
                "status": "enabled",
                "port": self.port,
                "metrics": {
                    "active_connections": "active_connections",
                    "database_queries": "database_queries_total",
                    "database_query_duration": "database_query_duration_seconds",
                    "cache_hits": "cache_hits_total",
                    "cache_misses": "cache_misses_total",
                    "message_published": "messages_published_total",
                    "message_consumed": "messages_consumed_total",
                    "business_events": "business_events_total",
                }
            }
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {"status": "error", "message": str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """Prometheus health check"""
        return {
            "status": "healthy" if self.enabled else "disabled",
            "enabled": self.enabled,
            "port": self.port,
        }
