import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.models.base_model import Base


class KnowledgeDoc(Base):
    __tablename__ = "knowledge_docs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    filename: Mapped[str] = mapped_column(String(300))
    
    file_type: Mapped[str] = mapped_column(String(20))
    # pdf | docx | txt | csv
    
    file_url: Mapped[str] = mapped_column(String(500))
    
    status: Mapped[str] = mapped_column(String(50), default="pending")
    # pending | processing | indexed | failed
    
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    
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
    chunks: Mapped[list] = relationship("KnowledgeChunk", back_populates="doc")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    doc_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_docs.id"),
        index=True
    )

    content: Mapped[str] = mapped_column(Text)

    # pgvector column — stores 1536-dim OpenAI embedding
    # Declared via DDL string because SQLAlchemy has no native Vector type
    # Alembic migration handles CREATE EXTENSION and the actual column type

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
    doc: Mapped["KnowledgeDoc"] = relationship(back_populates="chunks")

    # Note: the embedding column is added in migration (see migration note below)
