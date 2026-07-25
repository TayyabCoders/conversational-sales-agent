from dependency_injector.wiring import inject, Provide
from structlog import get_logger

logger = get_logger(__name__)


class ConversationController:
    @inject
    def __init__(
        self,
        conversation_mediator=Provide["conversation_mediator"],
        channel_repository=Provide["channel_repository"],
    ):
        self.conversation_mediator = conversation_mediator
        self.channel_repo = channel_repository

    async def list_conversations(self, status, channel: str | None, limit, offset):
        try:
            logger.info("ConversationController: Listing conversations...")

            # Resolve channel type slug → channel_id for the repo filter
            channel_id = None
            if channel:
                channel_record = await self.channel_repo.get_active_by_type(channel)
                channel_id = channel_record.id if channel_record else None

            result = await self.conversation_mediator.list_conversations(
                status=status, channel_id=channel_id, limit=limit, offset=offset,
            )

            logger.info("ConversationController: Conversations listed successfully.")
            return result

        except Exception as e:
            logger.error("ConversationController: Failed to list conversations.", exc_info=True)
            raise e

    async def get_conversation(self, conversation_id: str):
        try:
            logger.info(f"ConversationController: Getting conversation {conversation_id}...")
            result = await self.conversation_mediator.get_conversation(conversation_id)
            logger.info(f"ConversationController: Conversation {conversation_id} retrieved successfully.")
            return result
        except Exception as e:
            logger.error(f"ConversationController: Failed to get conversation {conversation_id}.", exc_info=True)
            raise e

    async def takeover(self, conversation_id: str, agent_id: str):
        try:
            logger.info(f"ConversationController: Taking over conversation {conversation_id}...")
            result = await self.conversation_mediator.takeover_conversation(conversation_id, agent_id)
            logger.info(f"ConversationController: Conversation {conversation_id} taken over successfully.")
            return result
        except Exception as e:
            logger.error(f"ConversationController: Failed to take over conversation {conversation_id}.", exc_info=True)
            raise e

    async def release(self, conversation_id: str):
        try:
            logger.info(f"ConversationController: Releasing conversation {conversation_id}...")
            result = await self.conversation_mediator.release_conversation(conversation_id)
            logger.info(f"ConversationController: Conversation {conversation_id} released successfully.")
            return result
        except Exception as e:
            logger.error(f"ConversationController: Failed to release conversation {conversation_id}.", exc_info=True)
            raise e
