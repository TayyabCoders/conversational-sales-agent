from typing import Optional
from app.repositories.base_repository import BaseRepository
from app.models.conversation_model import Conversation
from app.models.message_model import Message
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.di.container import container
from dependency_injector.wiring import inject, Provide
from structlog import get_logger
from typing import Any

logger = get_logger(__name__)


class ConversationRepository(BaseRepository[Conversation]):
    @inject
    def __init__(self, database = Provide["database"], cache: Optional[Any] = Provide["cache"]):
        super().__init__(Conversation, database, cache)

    async def get_or_create(
        self,
        customer_phone: str,
        channel: str,
        customer_name: str | None = None,
    ) -> Conversation:
        try:
            logger.info("ConversationRepository: Getting or creating conversation...")

            # Check if an active conversation already exists
            existing = await self.findOne(filters={
                "customer_phone": customer_phone,
                "channel": channel,
                "status": "active",
            })
            if existing:
                logger.info(f"ConversationRepository: Found existing conversation {existing.id}")
                return existing

            # Create new conversation
            conversation_data = {
                "customer_phone": customer_phone,
                "channel": channel,
                "customer_name": customer_name,
                "status": "active",
            }
            conversation = await self.create(conversation_data)

            logger.info(f"ConversationRepository: Created new conversation {conversation.id}")
            return conversation

        except Exception as e:
            logger.error("ConversationRepository: Failed to get or create conversation.", exc_info=True)
            raise e

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        media_type: str | None = None,
        media_url: str | None = None,
        tokens_used: int | None = None,
        latency_ms: int | None = None,
    ) -> Message:
        try:
            logger.info(f"ConversationRepository: Adding message to conversation {conversation_id}...")

            message_data = {
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "media_type": media_type,
                "media_url": media_url,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
            }
            message = await self.create(Message(**message_data))

            logger.info(f"ConversationRepository: Added message {message.id} to conversation {conversation_id}")
            return message

        except Exception as e:
            logger.error(f"ConversationRepository: Failed to add message to conversation {conversation_id}.", exc_info=True)
            raise e

    async def get_with_messages(self, conversation_id: str) -> Conversation | None:
        try:
            logger.info(f"ConversationRepository: Getting conversation {conversation_id} with messages...")

            # Get conversation
            conversation = await self.findById(conversation_id)
            if not conversation:
                logger.warning(f"ConversationRepository: Conversation {conversation_id} not found")
                return None

            # Get messages separately (since we're using BaseRepository pattern)
            from app.repositories.base_repository import BaseRepository
            message_repo = BaseRepository(Message, self.database, self.cache)
            messages = await message_repo.findAll(filters={"conversation_id": conversation_id})

            # Attach messages to conversation
            conversation.messages = messages

            logger.info(f"ConversationRepository: Retrieved conversation {conversation_id} with {len(messages)} messages")
            return conversation

        except Exception as e:
            logger.error(f"ConversationRepository: Failed to get conversation {conversation_id} with messages.", exc_info=True)
            raise e

    async def list_all(
        self,
        status: str | None = None,
        channel: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        try:
            logger.info("ConversationRepository: Listing conversations...")

            filters = {}
            if status:
                filters["status"] = status
            if channel:
                filters["channel"] = channel

            conversations = await self.findAll(filters=filters)
            
            # Apply pagination manually since BaseRepository doesn't have it built-in
            result = conversations[offset:offset + limit]

            logger.info(f"ConversationRepository: Listed {len(result)} conversations")
            return result

        except Exception as e:
            logger.error("ConversationRepository: Failed to list conversations.", exc_info=True)
            raise e

    async def update_status(
        self,
        conversation_id: str,
        status: str,
        agent_id: str | None = None,
    ) -> None:
        try:
            logger.info(f"ConversationRepository: Updating status for conversation {conversation_id}...")

            update_data = {"status": status}
            if agent_id:
                update_data["assigned_agent_id"] = agent_id

            await self.update(conversation_id, update_data)

            logger.info(f"ConversationRepository: Updated status for conversation {conversation_id}")

        except Exception as e:
            logger.error(f"ConversationRepository: Failed to update status for conversation {conversation_id}.", exc_info=True)
            raise e
