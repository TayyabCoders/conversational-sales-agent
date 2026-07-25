from fastapi import HTTPException
from app.configs.app_config import settings
from app.schemas.channels.whatsapp_schema import WhatsAppWebhookPayload
from app.schemas.webhook_schema import InboundMessage
from app.services.channels.adapters.base_adapter import BaseWebhookAdapter
from app.utils.security_util import verify_meta_signature


class WhatsAppWebhookAdapter(BaseWebhookAdapter):
    """
    Handles Meta (WhatsApp & Instagram) webhook verification and message parsing.
    Credentials come from the Channel DB record's config JSONB field.
    Falls back to env vars for local development.
    """

    def __init__(self, channel=None):
        """
        channel: Channel DB record (optional — falls back to settings if not provided)
        """
        self._channel = channel

    def _get_config(self, key: str, fallback=None):
        if self._channel and self._channel.config:
            return self._channel.config.get(key) or fallback
        return fallback

    async def verify_signature(self, body: bytes, headers: dict) -> None:
        signature = headers.get("x-hub-signature-256", "")
        secret = self._get_config("app_secret", settings.META_APP_SECRET)
        if not secret:
            raise HTTPException(500, "app_secret not configured for this channel")
        verify_meta_signature(body, signature, secret)

    async def parse_messages(self, data: dict) -> list[InboundMessage]:
        payload = WhatsAppWebhookPayload(**data)
        messages = []
        for entry in payload.entry:
            for change in entry.changes:
                for msg in (change.value.messages or []):
                    messages.append(InboundMessage(
                        sender_id=msg.from_,
                        message_id=msg.id,
                        text=msg.text.body if msg.text else None,
                        media_type=msg.type if msg.type != "text" else None,
                        media_id=(
                            (msg.audio and msg.audio.id) or
                            (msg.image and msg.image.id)
                        ) if msg.type != "text" else None,
                        contact_name=(
                            (change.value.contacts or [{}])[0]
                            .get("profile", {}).get("name")
                        ),
                    ))
        return messages

    async def verify_subscription(self, mode: str, challenge: str, token: str) -> str | None:
        expected = self._get_config("verify_token", settings.WHATSAPP_VERIFY_TOKEN)
        if not expected:
            raise HTTPException(500, "verify_token not configured for this channel")
        if mode != "subscribe" or token != expected:
            raise HTTPException(403, "Invalid verify token")
        return challenge
