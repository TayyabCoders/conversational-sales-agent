import uuid
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSON

from app.models.base_model import Base

if TYPE_CHECKING:
    from app.models.channel_model import Channel


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channels.id"),
        index=True,
    )

    customer_identifier: Mapped[str] = mapped_column(String(100), index=True)
    # phone number (WhatsApp/Instagram), user_id (Telegram), session UUID (web)

    customer_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    customer_email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    status: Mapped[str] = mapped_column(String(50), default="active")
    # active | escalated | resolved | closed

    assigned_agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    meta: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    channel: Mapped["Channel"] = relationship("Channel", back_populates="conversations")
    messages: Mapped[list] = relationship("Message", back_populates="conversation")
