from fastapi import HTTPException
from dependency_injector.wiring import inject, Provide
from app.schemas.channel_schema import ChannelCreate, ChannelUpdate
from structlog import get_logger

logger = get_logger(__name__)


class ChannelController:
    @inject
    def __init__(self, channel_repository=Provide["channel_repository"]):
        self.channel_repo = channel_repository

    async def list_channels(self):
        try:
            channels = await self.channel_repo.list_active()
            return channels
        except Exception as e:
            logger.error("ChannelController: failed to list channels", exc_info=True)
            raise e

    async def get_channel(self, channel_id: str):
        try:
            channel = await self.channel_repo.findById(channel_id)
            if not channel:
                raise HTTPException(404, "Channel not found")
            return channel
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"ChannelController: failed to get channel {channel_id}", exc_info=True)
            raise e

    async def create_channel(self, body: ChannelCreate):
        try:
            channel = await self.channel_repo.create({
                "type": body.type,
                "name": body.name,
                "config": body.config,
                "is_active": True,
            })
            logger.info(f"ChannelController: created channel {channel.id} ({channel.type})")
            return channel
        except Exception as e:
            logger.error("ChannelController: failed to create channel", exc_info=True)
            raise e

    async def update_channel(self, channel_id: str, body: ChannelUpdate):
        try:
            channel = await self.channel_repo.findById(channel_id)
            if not channel:
                raise HTTPException(404, "Channel not found")

            update_data = body.model_dump(exclude_none=True)
            updated = await self.channel_repo.update(channel_id, update_data)
            logger.info(f"ChannelController: updated channel {channel_id}")
            return updated
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"ChannelController: failed to update channel {channel_id}", exc_info=True)
            raise e

    async def delete_channel(self, channel_id: str):
        try:
            deleted = await self.channel_repo.delete(channel_id)
            if not deleted:
                raise HTTPException(404, "Channel not found")
            logger.info(f"ChannelController: deleted channel {channel_id}")
            return {"message": "Channel deleted"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"ChannelController: failed to delete channel {channel_id}", exc_info=True)
            raise e
