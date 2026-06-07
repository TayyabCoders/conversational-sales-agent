# Models Implementation — Step 1

This document outlines the implementation plan for database models in the AI Sales Agent project, adapted to the current project structure with tenant logic excluded.

---

## Overview

This step implements the core database models required for the MVP:
- **Conversation Model** — Tracks customer conversations across channels
- **Message Model** — Stores individual messages within conversations
- **Lead Model** — Manages lead scoring and qualification
- **KnowledgeDoc Model** — Stores uploaded knowledge base documents
- **KnowledgeChunk Model** — Stores indexed text chunks for RAG

**Note:** Tenant model and tenant-specific logic are deferred to a later phase.

---

## Current State Analysis

### Existing Models

#### `app/models/base_model.py`
- Status: ✅ Exists
- Uses SQLAlchemy `DeclarativeBase`
- No changes needed

#### `app/models/conversation_model.py`
- Status: ✅ Exists
- Missing: Relationship to `Message` model
- Current structure matches project pattern (manual `id`, `created_at`, `updated_at`)

#### `app/models/message_model.py`
- Status: ✅ Exists
- Missing: Relationship to `Conversation` model
- Missing: `media_url` field
- Current structure matches project pattern

#### `app/models/lead_model.py`
- Status: ✅ Exists
- Current structure matches project pattern

### Models to Create

#### `app/models/knowledge_doc_model.py`
- Status: ❌ Does not exist
- Needs: `KnowledgeDoc` and `KnowledgeChunk` models

---

## Implementation Details

### 1. Update `app/models/conversation_model.py`

Add relationship to messages:

```python
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSON

from app.models.base_model import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    channel: Mapped[str] = mapped_column(String(50))  # whatsapp|instagram|fb|web
    
    customer_phone: Mapped[str] = mapped_column(String(50), index=True)
    
    customer_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    status: Mapped[str] = mapped_column(String(50), default="active")
    # active | escalated | resolved | closed
    
    assigned_agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True
    )
    
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    # stores: detected_language, last_intent, ai_confidence
    
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
    messages: Mapped[list] = relationship("Message", back_populates="conversation")
```

**Changes:**
- Added `messages` relationship to Message model

---

### 2. Update `app/models/message_model.py`

Add relationship to conversation and `media_url` field:

```python
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
```

**Changes:**
- Added `media_url` field
- Added `conversation` relationship to Conversation model

---

### 3. Update `app/models/lead_model.py`

No changes needed - model is complete.

```python
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
    # {"budget": "50k", "timeline": "next month", "needs": [...]}
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
```

**Changes:**
- None - model already complete

---

### 4. Create `app/models/knowledge_doc_model.py`

Create new file with `KnowledgeDoc` and `KnowledgeChunk` models:

```python
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
```

**New file** with two models for knowledge base management.

---

### 5. Update `app/models/__init__.py`

Add imports for the new models:

```python
from typing import Any

from app.models.user_model import User
from app.models.conversation_model import Conversation
from app.models.message_model import Message
from app.models.lead_model import Lead
from app.models.knowledge_doc_model import KnowledgeDoc, KnowledgeChunk
from app.models.base_model import Base


async def initialize_models(database: Any) -> None:
    """Initialize database models by creating all tables.

    This uses the master engine from the Database wrapper to run
    SQLAlchemy's metadata.create_all synchronously within an async
    connection context.
    """
    # database is expected to be an instance of app.configs.database_config.Database
    engine = getattr(database, "master_engine", None)
    if engine is None:
        raise RuntimeError("Database master_engine is not initialized")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


__all__ = [
    "User",
    "Conversation",
    "Message",
    "Lead",
    "KnowledgeDoc",
    "KnowledgeChunk",
    "initialize_models"
]
```

**Changes:**
- Added imports for `KnowledgeDoc` and `KnowledgeChunk`
- Added to `__all__` list

---

## Database Migrations

Run Alembic migrations to create/update database tables:

```bash
# Generate migration for conversation model updates
alembic revision --autogenerate -m "update_conversation_model_add_relationships"

# Generate migration for message model updates
alembic revision --autogenerate -m "update_message_model_add_media_url_and_relationship"

# Generate migration for knowledge models
alembic revision --autogenerate -m "add_knowledge_doc_and_chunk_models"

# Apply all migrations
alembic upgrade head
```

**Note:** You can combine these into a single migration if preferred:
```bash
alembic revision --autogenerate -m "add_knowledge_models_and_update_existing_models"
alembic upgrade head
```

---

### pgvector Setup for Knowledge Chunks

Your Docker image `pgvector/pgvector:pg16` already has the extension. Add this to the `add_knowledge_models` migration file manually:

```python
# alembic/versions/xxxx_add_knowledge_models.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "knowledge_chunks",
        sa.Column("id",        sa.UUID(),    primary_key=True),
        sa.Column("doc_id",    sa.UUID(),    sa.ForeignKey("knowledge_docs.id"), index=True),
        sa.Column("content",   sa.Text(),    nullable=False),
        # 1536 dims = text-embedding-3-small
        sa.Column("embedding", sa.Text(),    nullable=True),   # stored as vector(1536)
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Change embedding column to actual vector type after creation
    op.execute("ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector")

    # IVFFlat index for fast ANN search (build after inserting data)
    op.execute(
        "CREATE INDEX knowledge_chunks_embedding_idx "
        "ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )

def downgrade():
    op.drop_table("knowledge_chunks")
```

---

## Implementation Checklist

- [ ] Update `app/models/conversation_model.py`
  - [ ] Add `messages` relationship
- [ ] Update `app/models/message_model.py`
  - [ ] Add `media_url` field
  - [ ] Add `conversation` relationship
- [ ] Update `app/models/lead_model.py`
  - [ ] No changes needed
- [ ] Create `app/models/knowledge_doc_model.py`
  - [ ] Create `KnowledgeDoc` model
  - [ ] Create `KnowledgeChunk` model
  - [ ] Add relationships
- [ ] Update `app/models/__init__.py`
  - [ ] Add imports for new models
  - [ ] Update `__all__` list
- [ ] Run Alembic migrations
  - [ ] Generate migration
  - [ ] Apply migration to database

---

## Notes

- **Tenant logic excluded** — All tenant-related fields and foreign keys have been excluded from this implementation. Tenant logic will be implemented in a later phase.
- **Project structure preserved** — All models follow the existing pattern of manual `id`, `created_at`, `updated_at` definitions and `Base` inheritance.
