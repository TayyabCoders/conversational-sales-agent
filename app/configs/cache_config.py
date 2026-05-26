"""
Redis cache manager with cluster support
"""
from typing import Any, Optional, Union
import json
import pickle
from redis import Redis, ConnectionPool
from redis.cluster import RedisCluster
from structlog import get_logger

logger = get_logger(__name__)


class RedisCache:
    """Redis cache manager with cluster support"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 7000,
        password: Optional[str] = None,
        db: int = 0,
        cluster_mode: bool = True,
        decode_responses: bool = True,
        max_connections: int = 20,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
    ):
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self.cluster_mode = cluster_mode
        self.decode_responses = decode_responses
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        
        # Redis client
        self.client: Optional[Union[Redis, RedisCluster]] = None
        self._connected = False
    
    async def connect(self) -> None:
        """Initialize Redis connection"""
        try:
            logger.info("Connecting to Redis...")
            
            if self.cluster_mode:
                # Cluster mode
                startup_nodes = [{"host": self.host, "port": self.port}]
                self.client = RedisCluster(
                    startup_nodes=startup_nodes,
                    password=self.password,
                    decode_responses=self.decode_responses,
                    max_connections_per_node=self.max_connections,
                    socket_timeout=self.socket_timeout,
                    socket_connect_timeout=self.socket_connect_timeout,
                    retry_on_timeout=True,
                    health_check_interval=30,
                )
            else:
                # Single node mode
                pool = ConnectionPool(
                    host=self.host,
                    port=self.port,
                    password=self.password,
                    db=self.db,
                    max_connections=self.max_connections,
                    socket_timeout=self.socket_timeout,
                    socket_connect_timeout=self.socket_connect_timeout,
                    retry_on_timeout=True,
                )
                self.client = Redis(
                    connection_pool=pool,
                    decode_responses=self.decode_responses,
                )
            
            # Test connection
            await self._test_connection()
            
            self._connected = True
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection"""
        try:
            logger.info("Disconnecting from Redis...")
            
            if self.client:
                self.client.close()
                self.client = None
            
            self._connected = False
            logger.info("Redis connection closed successfully")
            
        except Exception as e:
            logger.error(f"Error disconnecting from Redis: {e}")
    
    async def _test_connection(self) -> None:
        """Test Redis connection"""
        try:
            # Test with ping
            result = self.client.ping()
            if result:
                logger.debug("Redis connection test passed")
            else:
                raise Exception("Redis ping failed")
                
        except Exception as e:
            logger.error(f"Redis connection test failed: {e}")
            raise
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        if not self._connected:
            raise RuntimeError("Redis not connected")
        
        try:
            value = self.client.get(key)
            if value is None:
                return default
            
            # Try to deserialize JSON first, then pickle
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                try:
                    return pickle.loads(value.encode('latin1'))
                except (pickle.UnpicklingError, AttributeError):
                    return value
                    
        except Exception as e:
            logger.error(f"Redis get error for key '{key}': {e}")
            return default
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        serialize: bool = True,
    ) -> bool:
        """Set value in cache"""
        if not self._connected:
            raise RuntimeError("Redis not connected")
        
        try:
            if serialize:
                # Try JSON first, fallback to pickle
                try:
                    serialized_value = json.dumps(value)
                except (TypeError, ValueError):
                    serialized_value = pickle.dumps(value).decode('latin1')
            else:
                serialized_value = str(value)
            
            if ttl:
                return self.client.setex(key, ttl, serialized_value)
            else:
                return self.client.set(key, serialized_value)
                
        except Exception as e:
            logger.error(f"Redis set error for key '{key}': {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self._connected:
            raise RuntimeError("Redis not connected")
        
        try:
            result = self.client.delete(key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Redis delete error for key '{key}': {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self._connected:
            raise RuntimeError("Redis not connected")
        
        try:
            return bool(self.client.exists(key))
            
        except Exception as e:
            logger.error(f"Redis exists error for key '{key}': {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for key"""
        if not self._connected:
            raise RuntimeError("Redis not connected")
        
        try:
            return bool(self.client.expire(key, ttl))
            
        except Exception as e:
            logger.error(f"Redis expire error for key '{key}': {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Get TTL for key"""
        if not self._connected:
            raise RuntimeError("Redis not connected")
        
        try:
            return self.client.ttl(key)
            
        except Exception as e:
            logger.error(f"Redis TTL error for key '{key}': {e}")
            return -1
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern"""
        if not self._connected:
            raise RuntimeError("Redis not connected")
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
            
        except Exception as e:
            logger.error(f"Redis clear pattern error for '{pattern}': {e}")
            return 0
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        if not self._connected:
            raise RuntimeError("Redis not connected")
        
        try:
            return self.client.incr(key, amount)
            
        except Exception as e:
            logger.error(f"Redis increment error for key '{key}': {e}")
            return 0
    
    @property
    def connected(self) -> bool:
        """Check if Redis is connected"""
        return self._connected
    
    def health_check(self) -> dict:
        """Redis health check"""
        return {
            "status": "healthy" if self._connected else "unhealthy",
            "mode": "cluster" if self.cluster_mode else "single",
            "host": self.host,
            "port": self.port,
        }
