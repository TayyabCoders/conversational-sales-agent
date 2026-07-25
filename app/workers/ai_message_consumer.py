"""
Long-lived RabbitMQ consumer for AI message processing.
Started inside FastAPI lifespan via asyncio.create_task().
"""
import asyncio
from app.configs.messaging_config import RabbitMQClient
from app.configs.app_config import settings
from app.services.ai.agent_service import AgentService
from app.services.ai.rag_service import RAGService
from app.services.ai.memory_service import MemoryService
from app.services.ai.prompt_builder import PromptBuilder
from app.services.ai.guardrails_service import GuardrailsService
from app.services.ai.lead_scorer import LeadScorer
from app.services.ai.human_behavior_service import calculate_typing_delay
from app.services.channels import build_channel_client
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.channel_repository import ChannelRepository
from structlog import get_logger

logger = get_logger(__name__)


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
    payload keys: conversation_id, lead_id, message_text, media_type, media_id, channel_id
    """
    conversation_id = payload["conversation_id"]
    lead_id         = payload["lead_id"]
    message_text    = payload["message_text"]
    media_type      = payload.get("media_type")
    media_id        = payload.get("media_id")
    channel_id      = payload["channel_id"]

    try:
        await _process(
            conversation_id, lead_id,
            message_text, media_type, media_id, channel_id,
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
    channel_id: str,
) -> None:

    # --- Repositories ---
    conv_repo    = ConversationRepository()
    lead_repo    = LeadRepository()
    channel_repo = ChannelRepository()

    # --- Load channel record from DB → build client ---
    channel_record = await channel_repo.findById(channel_id)
    if not channel_record:
        logger.error(f"Channel {channel_id} not found in DB, cannot send response")
        return

    channel_client = build_channel_client(channel_record)

    # --- Handle voice or image if media present ---
    if media_type == "audio" and media_id:
        logger.info(f"Audio media detected for conversation {conversation_id} - transcription skipped")

    elif media_type == "image" and media_id:
        logger.info(f"Image media detected for conversation {conversation_id} - description skipped")

    # --- Check explicit escalation request ---
    guardrails = GuardrailsService()
    if guardrails.check_escalation_trigger(message_text):
        await _escalate(conversation_id, conv_repo)
        return

    # --- AI pipeline ---
    from openai import AsyncOpenAI
    import google.generativeai as genai
    from app.di.container import container

    db = container.resolve('database')
    db_session = db.get_session("read")

    use_gemini = settings.USE_GEMINI
    openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if not use_gemini else None
    gemini_client = None
    if use_gemini:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        gemini_client = genai.GenerativeModel(settings.GEMINI_MODEL)

    agent = AgentService(
        rag            = RAGService(
                             db=db_session,
                             openai=openai_client,
                             gemini_client=gemini_client,
                             use_gemini=use_gemini,
                         ),
        memory         = MemoryService(),
        prompt_builder = PromptBuilder(),
        guardrails     = guardrails,
        openai         = openai_client,
        gemini_client  = gemini_client,
    )

    ai_config = {
        "id": "default",
        "persona_name": "Assistant",
        "business_name": "",
        "tone": "friendly and professional",
        "hard_rules": [],
        "model": "gpt-4o" if not use_gemini else settings.GEMINI_MODEL,
        "temperature": 0.7,
        "max_tokens": 800,
        "use_gemini": use_gemini,
    }

    response_text, confidence = await agent.process_message(
        conversation_id=conversation_id,
        tenant_config=ai_config,
        message=message_text,
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
    conversation = await conv_repo.findById(conversation_id)
    if not conversation:
        logger.error(f"Conversation {conversation_id} not found, cannot send response")
        return

    sender_id = conversation.customer_identifier

    try:
        await channel_client.send_message(recipient=sender_id, message=response_text)
        logger.info(f"Message sent to {sender_id} via {channel_record.type} ({channel_record.name})")
    except Exception as e:
        logger.error(f"Failed to send message to {sender_id}: {e}", exc_info=True)
        raise  # Re-raise to trigger RabbitMQ retry/DLQ

    # --- Persist AI response (only after successful send) ---
    await conv_repo.add_message(
        conversation_id=conversation_id,
        role="assistant",
        content=response_text,
    )

    logger.info(f"AI response processed for conversation {conversation_id}")


async def _escalate(conversation_id: str, conv_repo: ConversationRepository) -> None:
    await conv_repo.update_status(conversation_id, "escalated")
    logger.info(f"Conversation {conversation_id} escalated to human")


async def _transcribe_voice(audio_bytes: bytes) -> str:
    import io
    if settings.USE_GEMINI:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = await model.generate_content_async([
            {"mime_type": "audio/ogg", "data": audio_bytes},
            "Transcribe this audio",
        ])
        return response.text
    else:
        from openai import AsyncOpenAI
        transcript = await AsyncOpenAI().audio.transcriptions.create(
            model="whisper-1",
            file=("voice.ogg", io.BytesIO(audio_bytes), "audio/ogg"),
        )
        return transcript.text


async def _describe_image(image_bytes: bytes, customer_text: str) -> str:
    import base64
    if settings.USE_GEMINI:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = await model.generate_content_async([
            {"mime_type": "image/jpeg", "data": image_bytes},
            customer_text or "What is in this image?",
        ])
        return response.text
    else:
        from openai import AsyncOpenAI
        b64 = base64.b64encode(image_bytes).decode()
        resp = await AsyncOpenAI().chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": customer_text or "What is in this image?"},
            ]}],
            max_tokens=500,
        )
        return resp.choices[0].message.content
