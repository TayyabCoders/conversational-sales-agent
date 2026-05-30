ok, from app.repositories.conversation_repository import ConversationRepository
from fastapi import HTTPException
from structlog import get_logger

logger = get_logger(__name__)


class ConversationController:
    @inject
    def __init__(self, conversation_repo = Provide["conversation_repository"]):
        self.repo = conversation_repo

    async def list_conversations(self, status, channel, limit, offset):
        try:
            logger.info("ConversationController: Listing conversations...")

            conversations = await self.repo.list_all(
                status=status, channel=channel, limit=limit, offset=offset,
            )

            logger.info("ConversationController: Conversations listed successfully.")
            return {"data": conversations, "total": len(conversations)}

        except Exception as e:
            logger.error("ConversationController: Failed to list conversations.", exc_info=True)
            raise e

    async def get_conversation(self, conversation_id: str):
        try:
            logger.info(f"ConversationController: Getting conversation {conversation_id}...")

            conv = await self.repo.get_with_messages(conversation_id)
            if not conv:
                raise HTTPException(404, "Conversation not found")

            logger.info(f"ConversationController: Conversation {conversation_id} retrieved successfully.")
            return conv

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"ConversationController: Failed to get conversation {conversation_id}.", exc_info=True)
            raise e

    async def takeover(self, conversation_id: str, agent_id: str):
        """Human agent takes over — AI stops responding."""
        try:
            logger.info(f"ConversationController: Taking over conversation {conversation_id}...")

            await self.repo.update_status(conversation_id, "escalated", agent_id=agent_id)

            logger.info(f"ConversationController: Conversation {conversation_id} taken over successfully.")
            return {"message": "Conversation assigned to you. AI has paused."}

        except Exception as e:
            logger.error(f"ConversationController: Failed to take over conversation {conversation_id}.", exc_info=True)
            raise e

    async def release(self, conversation_id: str):
        """Return conversation to AI."""
        try:
            logger.info(f"ConversationController: Releasing conversation {conversation_id}...")

            await self.repo.update_status(conversation_id, "active", agent_id=None)

            logger.info(f"ConversationController: Conversation {conversation_id} released successfully.")
            return {"message": "AI has resumed handling this conversation."}

        except Exception as e:
            logger.error(f"ConversationController: Failed to release conversation {conversation_id}.", exc_info=True)
            raise e
