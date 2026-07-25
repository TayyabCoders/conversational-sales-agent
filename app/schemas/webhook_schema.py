from pydantic import BaseModel
from typing import Optional


# ── Normalised inbound message (channel-agnostic) ────────────────
# WhatsApp-specific payload models live in app/schemas/channels/whatsapp_schema.py

class InboundMessage(BaseModel):
    sender_id: str           # phone (WhatsApp/Instagram), user_id (Telegram), session UUID (web)
    message_id: str
    text: Optional[str] = None
    media_type: Optional[str] = None  # audio | image | document
    media_id: Optional[str] = None
    contact_name: Optional[str] = None
