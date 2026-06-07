from app.di.container import container
from dependency_injector.wiring import inject, Provide
import json
from redis.asyncio import Redis
from structlog import get_logger

logger = get_logger(__name__)


class MemoryService:
    @inject
    def __init__(self, redis = Provide["redis_client"]):
        self.redis = redis
        self.window = 20
        self.ttl = 7200  # 2 hours

    def _key(self, conversation_id: str) -> str:
        return f"conv:memory:{conversation_id}"

    async def get_history(self, conversation_id: str) -> list[dict]:
        try:
            raw = await self.redis.get(self._key(conversation_id))
            return json.loads(raw) if raw else []
        except Exception as e:
            logger.error(f"MemoryService: Failed to get history for conversation {conversation_id}.", exc_info=True)
            return []

    async def append(self, conversation_id: str, role: str, content: str) -> None:
        try:
            history = await self.get_history(conversation_id)
            history.append({"role": role, "content": content})
            # Keep only last N messages (sliding window)
            history = history[-self.window:]
            await self.redis.setex(
                self._key(conversation_id), self.ttl, json.dumps(history)
            )
        except Exception as e:
            logger.error(f"MemoryService: Failed to append to history for conversation {conversation_id}.", exc_info=True)
            raise e

    async def clear(self, conversation_id: str) -> None:
        try:
            await self.redis.delete(self._key(conversation_id))
        except Exception as e:
            logger.error(f"MemoryService: Failed to clear history for conversation {conversation_id}.", exc_info=True)
            raise e
