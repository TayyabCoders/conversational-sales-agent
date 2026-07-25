import uuid
from app.di.container import container
from dependency_injector.wiring import inject, Provide
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.lead_repository import LeadRepository
from app.schemas.webhook_schema import InboundMessage
from app.configs.messaging_config import RabbitMQClient
from structlog import get_logger

logger = get_logger(__name__)


class MessageMediator:
    @inject
    def __init__(
        self,
        conversation_repo=Provide["conversation_repository"],
        lead_repo=Provide["lead_repository"],
        rabbitmq=Provide["rabbitmq"],
    ):
        self.conv_repo = conversation_repo
        self.lead_repo = lead_repo
        self.rabbitmq = rabbitmq

    async def handle_inbound(
        self,
        message: InboundMessage,
        channel_id: uuid.UUID,
    ) -> None:
        try:
            logger.info("MessageMediator: Handling inbound message...")

            # 1. Get or create conversation
            conversation = await self.conv_repo.get_or_create(
                customer_identifier=message.sender_id,
                channel_id=channel_id,
                customer_name=message.contact_name,
            )

            # 2. Persist raw customer message
            await self.conv_repo.add_message(
                conversation_id=str(conversation.id),
                role="user",
                content=message.text or "",
                media_type=message.media_type,
            )

            # 3. Skip AI if a human agent is handling this conversation
            if conversation.status == "escalated":
                logger.info(f"MessageMediator: Skipping AI — conv {conversation.id} is escalated to human")
                return

            # 4. Get or create lead record
            lead = await self.lead_repo.get_or_create(
                conversation_id=str(conversation.id),
                customer_identifier=message.sender_id,
            )

            # 5. Publish to RabbitMQ ai.messages queue — non-blocking
            await self.rabbitmq.publish(
                exchange="ai",
                routing_key="ai.messages",
                message=dict(
                    conversation_id=str(conversation.id),
                    lead_id=str(lead.id),
                    message_text=message.text or "",
                    media_type=message.media_type,
                    media_id=message.media_id,
                    channel_id=str(channel_id),
                ),
            )

            logger.info(f"MessageMediator: Queued AI task for conversation {conversation.id}")

        except Exception as e:
            logger.error("MessageMediator: Failed to handle inbound message.", exc_info=True)
            raise e
