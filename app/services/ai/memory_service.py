from dependency_injector.wiring import inject, Provide
import structlog

logger = structlog.get_logger(__name__)


class MemoryService:
    @inject
    def __init__(self, cache=Provide["cache"]):
        self.cache = cache
        self.window = 20
        self.ttl = 7200  # 2 hours

    def _key(self, conversation_id: str) -> str:
        return f"conv:memory:{conversation_id}"

    async def get_history(self, conversation_id: str) -> list[dict]:
        try:
            history = await self.cache.get(self._key(conversation_id))
            return history if isinstance(history, list) else []
        except Exception:
            logger.error(f"MemoryService: Failed to get history for conversation {conversation_id}.", exc_info=True)
            return []

    async def append(self, conversation_id: str, role: str, content: str) -> None:
        try:
            history = await self.get_history(conversation_id)
            history.append({"role": role, "content": content})
            history = history[-self.window:]
            await self.cache.set(self._key(conversation_id), history, ttl=self.ttl)
        except Exception:
            logger.error(f"MemoryService: Failed to append to history for conversation {conversation_id}.", exc_info=True)
            raise

    async def clear(self, conversation_id: str) -> None:
        try:
            await self.cache.delete(self._key(conversation_id))
        except Exception:
            logger.error(f"MemoryService: Failed to clear history for conversation {conversation_id}.", exc_info=True)
            raise
