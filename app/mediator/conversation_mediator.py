from app.di.container import container
from dependency_injector.wiring import inject, Provide
from structlog import get_logger

logger = get_logger(__name__)


class ConversationMediator:
    @inject
    def __init__(
        self,
        conversation_service = Provide["conversation_service"]
    ):
        self.conversation_service = conversation_service

    async def list_conversations(
        self,
        status: str = None,
        channel_id=None,
        limit: int = 50,
        offset: int = 0,
    ):
        try:
            logger.info("ConversationMediator: Listing conversations...")

            result = await self.conversation_service.list_conversations(
                status=status,
                channel_id=channel_id,
                limit=limit,
                offset=offset,
            )
            
            logger.info("ConversationMediator: Conversations listed successfully.")
            
            return result
        
        except Exception as e:
            logger.error("ConversationMediator: Failed to list conversations.", exc_info=True)
            raise e

    async def get_conversation(self, conversation_id: str):
        try:
            logger.info(f"ConversationMediator: Getting conversation {conversation_id}...")
            
            result = await self.conversation_service.get_conversation(conversation_id)
            
            logger.info(f"ConversationMediator: Conversation {conversation_id} retrieved successfully.")
            
            return result
        
        except Exception as e:
            logger.error(f"ConversationMediator: Failed to get conversation {conversation_id}.", exc_info=True)
            raise e

    async def takeover_conversation(self, conversation_id: str, agent_id: str):
        try:
            logger.info(f"ConversationMediator: Taking over conversation {conversation_id}...")
            
            result = await self.conversation_service.takeover_conversation(
                conversation_id,
                agent_id,
            )
            
            logger.info(f"ConversationMediator: Conversation {conversation_id} taken over successfully.")
            
            return result
        
        except Exception as e:
            logger.error(f"ConversationMediator: Failed to take over conversation {conversation_id}.", exc_info=True)
            raise e

    async def release_conversation(self, conversation_id: str):
        try:
            logger.info(f"ConversationMediator: Releasing conversation {conversation_id}...")
            
            result = await self.conversation_service.release_conversation(conversation_id)
            
            logger.info(f"ConversationMediator: Conversation {conversation_id} released successfully.")
            
            return result
        
        except Exception as e:
            logger.error(f"ConversationMediator: Failed to release conversation {conversation_id}.", exc_info=True)
            raise e
