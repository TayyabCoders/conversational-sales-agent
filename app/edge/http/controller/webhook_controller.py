from fastapi import Request, BackgroundTasks, HTTPException
from fastapi.responses import PlainTextResponse
from dependency_injector.wiring import inject, Provide
from app.mediator.message_mediator import MessageMediator
from app.schemas.webhook_schema import WhatsAppWebhookPayload, InboundMessage
from app.utils.security_util import verify_whatsapp_signature
from structlog import get_logger
import os

logger = get_logger(__name__)


class WebhookController:
    @inject
    def __init__(self, message_mediator = Provide["message_mediator"]):
        self.mediator = message_mediator

    async def handle_whatsapp(
        self,
        request: Request,
        background_tasks: BackgroundTasks,
    ):
        try:
            logger.info("WebhookController: Handling WhatsApp webhook...")

            # 1. Verify Meta HMAC-SHA256 — raises 403 if invalid
            body = await request.body()
            signature = request.headers.get("X-Hub-Signature-256", "")
            verify_whatsapp_signature(body, signature)

            # 2. Parse Meta payload
            data = await request.json()
            payload = WhatsAppWebhookPayload(**data)

            # 3. Extract each message and queue (non-blocking)
            for entry in payload.entry:
                for change in entry.changes:
                    for msg in (change.value.messages or []):
                        inbound = InboundMessage(
                            from_number=msg.from_,
                            message_id=msg.id,
                            text=msg.text.body if msg.text else None,
                            media_type=msg.type if msg.type != "text" else None,
                            media_id=(msg.audio or msg.image or {}).get("id") if msg.type != "text" else None,
                            contact_name=(change.value.contacts or [{}])[0].get("profile", {}).get("name"),
                        )
                        background_tasks.add_task(
                            self.mediator.handle_inbound,
                            message=inbound,
                            channel="whatsapp",
                        )

            # MUST return 200 fast — Meta retries if it doesn't get 200
            logger.info("WebhookController: WhatsApp webhook handled successfully.")
            return {"status": "ok"}

        except Exception as e:
            logger.error("WebhookController: Failed to handle WhatsApp webhook.", exc_info=True)
            raise e

    async def verify_whatsapp(
        self,
        mode: str,
        challenge: str,
        verify_token: str,
    ):
        try:
            logger.info("WebhookController: Verifying WhatsApp webhook...")

            # Use environment variable for verify token (tenant logic excluded)
            expected_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
            if not expected_token:
                raise HTTPException(500, "WhatsApp verify token not configured")

            if verify_token != expected_token:
                raise HTTPException(403, "Invalid verify token")

            logger.info("WebhookController: WhatsApp webhook verified successfully.")
            return PlainTextResponse(challenge)

        except HTTPException:
            raise
        except Exception as e:
            logger.error("WebhookController: Failed to verify WhatsApp webhook.", exc_info=True)
            raise e
