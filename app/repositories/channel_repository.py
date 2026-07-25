from typing import Optional, Any
from app.repositories.base_repository import BaseRepository
from app.models.channel_model import Channel
from dependency_injector.wiring import inject, Provide
from structlog import get_logger

logger = get_logger(__name__)


class ChannelRepository(BaseRepository[Channel]):
    @inject
    def __init__(self, database=Provide["database"], cache: Optional[Any] = Provide["cache"]):
        super().__init__(Channel, database, cache)

    async def get_active_by_type(self, channel_type: str) -> Optional[Channel]:
        """Return the first active channel of the given type (whatsapp, telegram, etc.)."""
        try:
            return await self.findOne(filters={"type": channel_type, "is_active": True})
        except Exception as e:
            logger.error(f"ChannelRepository: failed to find channel by type {channel_type!r}", exc_info=True)
            raise e

    async def list_active(self) -> list[Channel]:
        try:
            return await self.findAll(filters={"is_active": True})
        except Exception as e:
            logger.error("ChannelRepository: failed to list active channels", exc_info=True)
            raise e
