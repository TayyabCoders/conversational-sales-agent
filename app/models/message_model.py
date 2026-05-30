import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.models.base_model import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id"),
        index=True
    )
    
    role: Mapped[str] = mapped_column(String(20))  # user|assistant|system
    
    content: Mapped[str] = mapped_column(Text)
    
    media_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # text | image | audio | document
    
    media_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationship
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
