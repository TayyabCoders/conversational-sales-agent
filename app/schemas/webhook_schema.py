from pydantic import BaseModel, Field
from typing import Optional, List


# ── WhatsApp Cloud API payload structure ──────────────────────────

class WhatsAppTextMessage(BaseModel):
    body: str


class WhatsAppAudio(BaseModel):
    id: str
    mime_type: Optional[str] = None


class WhatsAppImage(BaseModel):
    id: str
    mime_type: Optional[str] = None


class WhatsAppMessage(BaseModel):
    id: str
    from_: str = Field(alias="from")
    timestamp: str
    type: str  # text | audio | image | document
    text: Optional[WhatsAppTextMessage] = None
    audio: Optional[WhatsAppAudio] = None
    image: Optional[WhatsAppImage] = None


class WhatsAppContact(BaseModel):
    profile: Optional[dict] = None
    wa_id: Optional[str] = None


class WhatsAppValue(BaseModel):
    messaging_product: str
    metadata: Optional[dict] = None
    messages: Optional[List[WhatsAppMessage]] = None
    contacts: Optional[List[WhatsAppContact]] = None


class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: str


class WhatsAppEntry(BaseModel):
    id: str
    changes: List[WhatsAppChange]


class WhatsAppWebhookPayload(BaseModel):
    object: str
    entry: List[WhatsAppEntry]


# ── Normalised inbound message (channel-agnostic) ────────────────

class InboundMessage(BaseModel):
    from_number: str
    message_id: str
    text: Optional[str] = None
    media_type: Optional[str] = None  # audio | image | document
    media_id: Optional[str] = None  # Meta media ID to download
    contact_name: Optional[str] = None