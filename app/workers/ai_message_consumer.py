"""
Long-lived RabbitMQ consumer for AI message processing.
Started inside FastAPI lifespan via asyncio.create_task().
"""
import asyncio
import logging
from app.configs.messaging_config import RabbitMQClient
from app.configs.app_config import get_settings
from app.services.ai.agent_service import AgentService
from app.services.ai.rag_service import RAGService
from app.services.ai.memory_service import MemoryService
from app.services.ai.prompt_builder import PromptBuilder
from app.services.ai.guardrails_service import GuardrailsService
from app.services.ai.lead_scorer import LeadScorer
from app.services.ai.human_behavior_service import calculate_typing_delay
from app.services.channels.whatsapp_channel import WhatsAppChannel
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.lead_repository import LeadRepository
from structlog import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def start_ai_message_consumer(rabbitmq: RabbitMQClient) -> None:
    """
    Bind to exchange="ai", routing_key="ai.messages".
    Called once in main.py lifespan startup.
    """
    await rabbitmq.consume(
        exchange     = "ai",
        queue_name   = "ai.messages.queue",
        routing_keys = ["ai.messages"],
        callback     = handle_message,
    )
    logger.info("AI message consumer started — listening on ai.messages.queue")


async def handle_message(payload: dict) -> None:
    """
    Called by RabbitMQClient for every message on ai.messages.queue.
    payload keys: conversation_id, lead_id, message_text, media_type, media_id, channel
    """
    conversation_id = payload["conversation_id"]
    lead_id         = payload["lead_id"]
    message_text    = payload["message_text"]
    media_type      = payload.get("media_type")
    media_id        = payload.get("media_id")
    channel         = payload["channel"]

    try:
        await _process(
            conversation_id, lead_id,
            message_text, media_type, media_id, channel,
        )
    except Exception as exc:
        logger.error(f"AI message processing failed: {exc}", exc_info=True)
        raise   # RabbitMQ will re-queue (message.process() context manager)


async def _process(
    conversation_id: str,
    lead_id: str,
    message_text: str,
    media_type: str | None,
    media_id: str | None,
    channel: str,
) -> None:

    # --- Repositories ---
    conv_repo   = ConversationRepository()
    lead_repo   = LeadRepository()

    channel_client = WhatsAppChannel(
        api_version = settings.WHATSAPP_API_VERSION,
        app_secret  = settings.META_APP_SECRET,
    )

    # --- Handle voice or image if media present ---
    # Note: Media handling requires tenant-specific access tokens, skipped for now
    if media_type == "audio" and media_id:
        logger.info(f"Audio media detected for conversation {conversation_id} - transcription skipped (tenant logic excluded)")
        # audio_bytes  = await channel_client.download_media(media_id, access_token=tenant.whatsapp_access_token)
        # message_text = await _transcribe_voice(audio_bytes)

    elif media_type == "image" and media_id:
        logger.info(f"Image media detected for conversation {conversation_id} - description skipped (tenant logic excluded)")
        # image_bytes  = await channel_client.download_media(media_id, access_token=tenant.whatsapp_access_token)
        # message_text = await _describe_image(image_bytes, message_text)

    # --- Check explicit escalation request ---
    guardrails = GuardrailsService()
    if guardrails.check_escalation_trigger(message_text):
        await _escalate(conversation_id, conv_repo)
        return

    # --- AI pipeline ---
    from openai import AsyncOpenAI
    from qdrant_client import AsyncQdrantClient

    agent = AgentService(
        rag            = RAGService(
                             qdrant     = AsyncQdrantClient(url=settings.QDRANT_URL),
                             openai     = AsyncOpenAI(api_key=settings.OPENAI_API_KEY),
                             collection = settings.QDRANT_COLLECTION,
                         ),
        memory         = MemoryService(redis=..., window=settings.AI_MEMORY_WINDOW),
        prompt_builder = PromptBuilder(),
        guardrails     = guardrails,
        openai         = AsyncOpenAI(api_key=settings.OPENAI_API_KEY),
    )

    # Use default AI config (tenant logic excluded)
    ai_config = {
        "id": "default",
        "persona_name": "Assistant",
        "business_name": "",
        "tone": "friendly and professional",
        "hard_rules": [],
        "model": "gpt-4o",
        "temperature": 0.7,
        "max_tokens": 800,
    }

    response_text, confidence = await agent.process_message(
        conversation_id = conversation_id,
        tenant_config   = ai_config,
        message         = message_text,
    )

    # --- Low confidence → escalate ---
    threshold = ai_config.get("confidence_threshold", settings.AI_CONFIDENCE_THRESHOLD)
    if confidence < threshold:
        await _escalate(conversation_id, conv_repo)
        return

    # --- Update lead score ---
    scorer = LeadScorer(lead_repo)
    await scorer.update_from_message(lead_id, message_text)

    # --- Human-like delay ---
    await asyncio.sleep(calculate_typing_delay(response_text))

    # --- Send via channel ---
    # Note: WhatsApp sending requires tenant-specific credentials, skipped for now
    logger.info(f"AI response generated for conversation {conversation_id} - sending skipped (tenant logic excluded)")
    # await channel_client.send_message(
    #     recipient       = tenant.customer_phone,
    #     message         = response_text,
    #     phone_number_id = tenant.whatsapp_phone_id,
    #     access_token    = tenant.whatsapp_access_token,
    # )

    # --- Persist AI response ---
    await conv_repo.add_message(
        conversation_id = conversation_id,
        role            = "assistant",
        content         = response_text,
    )

    logger.info(f"AI response processed for conversation {conversation_id}")


async def _escalate(conversation_id: str, conv_repo: ConversationRepository) -> None:
    await conv_repo.update_status(conversation_id, "escalated")
    logger.info(f"Conversation {conversation_id} escalated to human")


async def _transcribe_voice(audio_bytes: bytes) -> str:
    from openai import AsyncOpenAI
    import io
    transcript = await AsyncOpenAI().audio.transcriptions.create(
        model = "whisper-1",
        file  = ("voice.ogg", io.BytesIO(audio_bytes), "audio/ogg"),
    )
    return transcript.text


async def _describe_image(image_bytes: bytes, customer_text: str) -> str:
    import base64
    from openai import AsyncOpenAI
    b64  = base64.b64encode(image_bytes).decode()
    resp = await AsyncOpenAI().chat.completions.create(
        model    = "gpt-4o",
        messages = [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            {"type": "text",      "text": customer_text or "What is in this image?"},
        ]}],
        max_tokens = 500,
    )
    return resp.choices[0].message.content
