import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSON

from app.models.base_model import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id")
    )
    
    customer_phone: Mapped[str] = mapped_column(String(50), index=True)
    
    customer_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    customer_email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    score: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    
    stage: Mapped[str] = mapped_column(String(50), default="cold")
    # cold | warm | hot | qualified | converted
    
    qualification_data: Mapped[dict] = mapped_column(JSON, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
