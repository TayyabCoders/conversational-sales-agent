import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base_model import Base


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    type: Mapped[str] = mapped_column(String(50), index=True)
    # whatsapp | instagram | telegram | web

    name: Mapped[str] = mapped_column(String(200))
    # Human-readable label e.g. "Main WhatsApp", "Support Bot"

    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Channel-specific credentials:
    #   whatsapp/instagram: {phone_number_id, access_token, app_secret, verify_token, api_version}
    #   telegram:           {bot_token}
    #   web:                {api_key}

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    conversations: Mapped[list] = relationship("Conversation", back_populates="channel")
