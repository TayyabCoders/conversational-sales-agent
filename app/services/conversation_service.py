from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from structlog import get_logger
from dependency_injector.wiring import inject, Provide

logger = get_logger(__name__)


class ConversationService:
    @inject
    def __init__(
        self,
        conversation_repository = Provide["conversation_repository"],
        prometheus = Provide["prometheus"],
    ):
        self.conversation_repository = conversation_repository
        self.prometheus = prometheus

    async def list_conversations(
        self,
        status: Optional[str] = None,
        channel_id=None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        try:
            logger.info("ConversationService: Listing conversations...")

            conversations = await self.conversation_repository.list_all(
                status=status,
                channel_id=channel_id,
                limit=limit,
                offset=offset,
            )
            
            logger.info(f"ConversationService: Listed {len(conversations)} conversations")
            
            # Record business event
            self.prometheus.record_business_event("conversation_list", "success")
            
            return {"data": conversations, "total": len(conversations)}
        
        except Exception as e:
            logger.error("ConversationService: Failed to list conversations.", exc_info=True)
            raise e

    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        try:
            logger.info(f"ConversationService: Getting conversation {conversation_id}...")
            
            conversation = await self.conversation_repository.get_with_messages(conversation_id)
            
            if not conversation:
                logger.warning(f"ConversationService: Conversation {conversation_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found"
                )
            
            logger.info(f"ConversationService: Retrieved conversation {conversation_id}")
            
            # Record business event
            self.prometheus.record_business_event("conversation_get", "success")
            
            return conversation
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"ConversationService: Failed to get conversation {conversation_id}.", exc_info=True)
            raise e

    async def takeover_conversation(
        self,
        conversation_id: str,
        agent_id: str,
    ) -> Dict[str, Any]:
        try:
            logger.info(f"ConversationService: Taking over conversation {conversation_id}...")
            
            await self.conversation_repository.update_status(
                conversation_id,
                "escalated",
                agent_id=agent_id,
            )
            
            logger.info(f"ConversationService: Conversation {conversation_id} taken over by agent {agent_id}")
            
            # Record business event
            self.prometheus.record_business_event("conversation_takeover", "success")
            
            return {"message": "Conversation assigned to you. AI has paused."}
        
        except Exception as e:
            logger.error(f"ConversationService: Failed to take over conversation {conversation_id}.", exc_info=True)
            raise e

    async def release_conversation(self, conversation_id: str) -> Dict[str, Any]:
        try:
            logger.info(f"ConversationService: Releasing conversation {conversation_id}...")
            
            await self.conversation_repository.update_status(
                conversation_id,
                "active",
                agent_id=None,
            )
            
            logger.info(f"ConversationService: Conversation {conversation_id} released back to AI")
            
            # Record business event
            self.prometheus.record_business_event("conversation_release", "success")
            
            return {"message": "AI has resumed handling this conversation."}
        
        except Exception as e:
            logger.error(f"ConversationService: Failed to release conversation {conversation_id}.", exc_info=True)
            raise e
