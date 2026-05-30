# Repositories Implementation — Step 7

This document outlines the implementation plan for repositories in the AI Sales Agent project, adapted to the current project structure with tenant logic excluded.

---

## Overview

This step implements the repositories required for database operations:
- **ConversationRepository** — Manages conversation and message CRUD operations
- **LeadRepository** — Manages lead CRUD operations and scoring
- **KnowledgeRepository** — Manages knowledge document CRUD operations

**Note:** Tenant repository and tenant-specific logic are excluded from this implementation. Tenant logic will be implemented in a later phase.

---

## Current State Analysis

### Existing Repositories

#### `app/repositories/base_repository.py`
- Status: ✅ Exists
- Generic repository with common CRUD operations
- Uses `database` and `cache` dependencies
- Uses structlog for logging
- Has try/except blocks with logging

#### `app/repositories/user_repository.py`
- Status: ✅ Exists
- Inherits from `BaseRepository[User]`
- Uses `@inject` decorator on `__init__`
- Uses `Provide["database"]` and `Provide["cache"]` for dependency injection
- Uses structlog for logging
- Has try/except blocks with logging

### Repositories to Create

#### `app/repositories/conversation_repository.py`
- Status: ❌ Does not exist
- Needs: get_or_create, add_message, get_with_messages, list_all, update_status methods

#### `app/repositories/lead_repository.py`
- Status: ❌ Does not exist
- Needs: get_or_create, update_stage, list_all methods

#### `app/repositories/knowledge_repository.py`
- Status: ❌ Does not exist
- Needs: create, update_status, list_all, delete_qdrant_chunks methods

---

## Implementation Details

### 1. Create `app/repositories/conversation_repository.py`

Create new file with conversation repository:

```python
from typing import Optional
from app.repositories.base_repository import BaseRepository
from app.models.conversation_model import Conversation
from app.models.message_model import Message
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.di.container import container
from dependency_injector.wiring import inject, Provide
from structlog import get_logger
from typing import Any

logger = get_logger(__name__)


class ConversationRepository(BaseRepository[Conversation]):
    @inject
    def __init__(self, database = Provide["database"], cache: Optional[Any] = Provide["cache"]):
        super().__init__(Conversation, database, cache)

    async def get_or_create(
        self,
        customer_phone: str,
        channel: str,
        customer_name: str | None = None,
    ) -> Conversation:
        try:
            logger.info("ConversationRepository: Getting or creating conversation...")

            # Check if an active conversation already exists
            existing = await self.findOne(filters={
                "customer_phone": customer_phone,
                "channel": channel,
                "status": "active",
            })
            if existing:
                logger.info(f"ConversationRepository: Found existing conversation {existing.id}")
                return existing

            # Create new conversation
            conversation_data = {
                "customer_phone": customer_phone,
                "channel": channel,
                "customer_name": customer_name,
                "status": "active",
            }
            conversation = await self.create(conversation_data)

            logger.info(f"ConversationRepository: Created new conversation {conversation.id}")
            return conversation

        except Exception as e:
            logger.error("ConversationRepository: Failed to get or create conversation.", exc_info=True)
            raise e

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        media_type: str | None = None,
        media_url: str | None = None,
        tokens_used: int | None = None,
        latency_ms: int | None = None,
    ) -> Message:
        try:
            logger.info(f"ConversationRepository: Adding message to conversation {conversation_id}...")

            message_data = {
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "media_type": media_type,
                "media_url": media_url,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
            }
            message = await self.create(Message(**message_data))

            logger.info(f"ConversationRepository: Added message {message.id} to conversation {conversation_id}")
            return message

        except Exception as e:
            logger.error(f"ConversationRepository: Failed to add message to conversation {conversation_id}.", exc_info=True)
            raise e

    async def get_with_messages(self, conversation_id: str) -> Conversation | None:
        try:
            logger.info(f"ConversationRepository: Getting conversation {conversation_id} with messages...")

            # Get conversation
            conversation = await self.findById(conversation_id)
            if not conversation:
                logger.warning(f"ConversationRepository: Conversation {conversation_id} not found")
                return None

            # Get messages separately (since we're using BaseRepository pattern)
            from app.repositories.base_repository import BaseRepository
            message_repo = BaseRepository(Message, self.database, self.cache)
            messages = await message_repo.findAll(filters={"conversation_id": conversation_id})

            # Attach messages to conversation
            conversation.messages = messages

            logger.info(f"ConversationRepository: Retrieved conversation {conversation_id} with {len(messages)} messages")
            return conversation

        except Exception as e:
            logger.error(f"ConversationRepository: Failed to get conversation {conversation_id} with messages.", exc_info=True)
            raise e

    async def list_all(
        self,
        status: str | None = None,
        channel: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        try:
            logger.info("ConversationRepository: Listing conversations...")

            filters = {}
            if status:
                filters["status"] = status
            if channel:
                filters["channel"] = channel

            conversations = await self.findAll(filters=filters)
            
            # Apply pagination manually since BaseRepository doesn't have it built-in
            result = conversations[offset:offset + limit]

            logger.info(f"ConversationRepository: Listed {len(result)} conversations")
            return result

        except Exception as e:
            logger.error("ConversationRepository: Failed to list conversations.", exc_info=True)
            raise e

    async def update_status(
        self,
        conversation_id: str,
        status: str,
        agent_id: str | None = None,
    ) -> None:
        try:
            logger.info(f"ConversationRepository: Updating status for conversation {conversation_id}...")

            update_data = {"status": status}
            if agent_id:
                update_data["assigned_agent_id"] = agent_id

            await self.update(conversation_id, update_data)

            logger.info(f"ConversationRepository: Updated status for conversation {conversation_id}")

        except Exception as e:
            logger.error(f"ConversationRepository: Failed to update status for conversation {conversation_id}.", exc_info=True)
            raise e
```

**Changes from build plan:**
- Removed `tenant_id` parameter from all methods (tenant logic excluded)
- Adapted to use BaseRepository pattern instead of direct AsyncSession
- Uses `@inject` decorator on `__init__` following project pattern
- Uses `Provide["database"]` and `Provide["cache"]` for dependency injection
- Added try/except blocks with logging following project pattern
- Changed from `logging` to `structlog`

---

### 2. Create `app/repositories/lead_repository.py`

Create new file with lead repository:

```python
from typing import Optional
from app.repositories.base_repository import BaseRepository
from app.models.lead_model import Lead
from app.di.container import container
from dependency_injector.wiring import inject, Provide
from structlog import get_logger
from typing import Any

logger = get_logger(__name__)


class LeadRepository(BaseRepository[Lead]):
    @inject
    def __init__(self, database = Provide["database"], cache: Optional[Any] = Provide["cache"]):
        super().__init__(Lead, database, cache)

    async def get_or_create(
        self,
        conversation_id: str,
        customer_phone: str,
    ) -> Lead:
        try:
            logger.info("LeadRepository: Getting or creating lead...")

            # Check if lead already exists for this conversation
            existing = await self.findOne(filters={"conversation_id": conversation_id})
            if existing:
                logger.info(f"LeadRepository: Found existing lead {existing.id}")
                return existing

            # Create new lead
            lead_data = {
                "conversation_id": conversation_id,
                "customer_phone": customer_phone,
                "score": 0,
                "stage": "cold",
            }
            lead = await self.create(lead_data)

            logger.info(f"LeadRepository: Created new lead {lead.id}")
            return lead

        except Exception as e:
            logger.error("LeadRepository: Failed to get or create lead.", exc_info=True)
            raise e

    async def update_stage(self, lead_id: str, stage: str) -> None:
        try:
            logger.info(f"LeadRepository: Updating stage for lead {lead_id}...")

            await self.update(lead_id, {"stage": stage})

            logger.info(f"LeadRepository: Updated stage for lead {lead_id}")

        except Exception as e:
            logger.error(f"LeadRepository: Failed to update stage for lead {lead_id}.", exc_info=True)
            raise e

    async def list_all(
        self,
        stage: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Lead]:
        try:
            logger.info("LeadRepository: Listing leads...")

            filters = {}
            if stage:
                filters["stage"] = stage

            leads = await self.findAll(filters=filters)
            
            # Apply pagination manually
            result = leads[offset:offset + limit]

            logger.info(f"LeadRepository: Listed {len(result)} leads")
            return result

        except Exception as e:
            logger.error("LeadRepository: Failed to list leads.", exc_info=True)
            raise e
```

**Changes from build plan:**
- Removed `tenant_id` parameter from all methods (tenant logic excluded)
- Renamed `update_score` to `update_stage` to match controller usage
- Adapted to use BaseRepository pattern instead of direct AsyncSession
- Uses `@inject` decorator on `__init__` following project pattern
- Uses `Provide["database"]` and `Provide["cache"]` for dependency injection
- Added try/except blocks with logging following project pattern
- Changed from `logging` to `structlog`

---

### 3. Create `app/repositories/knowledge_repository.py`

Create new file with knowledge repository:

```python
from typing import Optional
from app.repositories.base_repository import BaseRepository
from app.models.knowledge_doc_model import KnowledgeDoc
from app.models.knowledge_doc_model import KnowledgeChunk
from sqlalchemy import delete
from app.di.container import container
from dependency_injector.wiring import inject, Provide
from structlog import get_logger
from typing import Any

logger = get_logger(__name__)


class KnowledgeRepository(BaseRepository[KnowledgeDoc]):
    @inject
    def __init__(self, database = Provide["database"], cache: Optional[Any] = Provide["cache"]):
        super().__init__(KnowledgeDoc, database, cache)

    async def create(
        self,
        filename: str,
        file_type: str,
        file_url: str,
    ) -> KnowledgeDoc:
        try:
            logger.info(f"KnowledgeRepository: Creating knowledge doc {filename}...")

            doc_data = {
                "filename": filename,
                "file_type": file_type,
                "file_url": file_url,
                "status": "pending",
                "chunk_count": 0,
            }
            doc = await super().create(doc_data)

            logger.info(f"KnowledgeRepository: Created knowledge doc {doc.id}")
            return doc

        except Exception as e:
            logger.error(f"KnowledgeRepository: Failed to create knowledge doc {filename}.", exc_info=True)
            raise e

    async def update_status(self, doc_id: str, status: str, chunk_count: int = 0) -> None:
        try:
            logger.info(f"KnowledgeRepository: Updating status for doc {doc_id}...")

            update_data = {"status": status}
            if chunk_count > 0:
                update_data["chunk_count"] = chunk_count

            await self.update(doc_id, update_data)

            logger.info(f"KnowledgeRepository: Updated status for doc {doc_id}")

        except Exception as e:
            logger.error(f"KnowledgeRepository: Failed to update status for doc {doc_id}.", exc_info=True)
            raise e

    async def list_all(self) -> list[KnowledgeDoc]:
        try:
            logger.info("KnowledgeRepository: Listing knowledge docs...")

            docs = await self.findAll()

            logger.info(f"KnowledgeRepository: Listed {len(docs)} knowledge docs")
            return docs

        except Exception as e:
            logger.error("KnowledgeRepository: Failed to list knowledge docs.", exc_info=True)
            raise e

    async def delete_qdrant_chunks(self, doc_id: str) -> None:
        try:
            logger.info(f"KnowledgeRepository: Deleting chunks for doc {doc_id}...")

            # Delete from PostgreSQL chunks table
            chunk_repo = BaseRepository(KnowledgeChunk, self.database, self.cache)
            await chunk_repo.deleteWhere(filters={"doc_id": doc_id})

            logger.info(f"KnowledgeRepository: Deleted chunks for doc {doc_id}")
            # Note: Qdrant deletion is handled in knowledge_indexer worker

        except Exception as e:
            logger.error(f"KnowledgeRepository: Failed to delete chunks for doc {doc_id}.", exc_info=True)
            raise e
```

**Changes from build plan:**
- Removed `tenant_id` parameter from all methods (tenant logic excluded)
- Removed `tenant_id` from `delete_qdrant_chunks` method
- Adapted to use BaseRepository pattern instead of direct AsyncSession
- Uses `@inject` decorator on `__init__` following project pattern
- Uses `Provide["database"]` and `Provide["cache"]` for dependency injection
- Added try/except blocks with logging following project pattern
- Changed from `logging` to `structlog`

---

### 4. Update `app/repositories/__init__.py`

Add imports for the new repositories (if file exists, otherwise create it):

```python
from app.repositories.user_repository import UserRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.knowledge_repository import KnowledgeRepository
from app.repositories.base_repository import BaseRepository

__all__ = [
    "UserRepository",
    "ConversationRepository",
    "LeadRepository",
    "KnowledgeRepository",
    "BaseRepository",
]
```

**Note:** Check if `__init__.py` exists in the repositories directory. If not, create it with the above content.

---

## Implementation Checklist

- [ ] Create `app/repositories/conversation_repository.py`
  - [ ] Create get_or_create method
  - [ ] Create add_message method
  - [ ] Create get_with_messages method
  - [ ] Create list_all method
  - [ ] Create update_status method
  - [ ] Remove tenant_id parameters
  - [ ] Add proper imports and logging
- [ ] Create `app/repositories/lead_repository.py`
  - [ ] Create get_or_create method
  - [ ] Create update_stage method
  - [ ] Create list_all method
  - [ ] Remove tenant_id parameters
  - [ ] Add proper imports and logging
- [ ] Create `app/repositories/knowledge_repository.py`
  - [ ] Create create method
  - [ ] Create update_status method
  - [ ] Create list_all method
  - [ ] Create delete_qdrant_chunks method
  - [ ] Remove tenant_id parameters
  - [ ] Add proper imports and logging
- [ ] Update/Create `app/repositories/__init__.py`
  - [ ] Add imports for new repositories
  - [ ] Update `__all__` list

---

## Notes

- **Tenant logic excluded** — All `tenant_id` parameters have been removed from repository methods. Tenant logic will be implemented in a later phase.
- **Project structure preserved** — All repositories follow the existing pattern of inheriting from `BaseRepository[T]`, using `@inject` decorator on `__init__`, `Provide["database"]` and `Provide["cache"]` for dependency injection, structlog for logging, and try/except blocks with logging.
- **BaseRepository pattern** — Adapted from build plan's direct AsyncSession usage to the project's BaseRepository pattern which uses `database.get_session()` internally.
- **Method naming** — Renamed `update_score` to `update_stage` in LeadRepository to match the controller's usage.
- **Message handling** — `get_with_messages` manually attaches messages since BaseRepository doesn't support eager loading out of the box.
- **Qdrant deletion** — Qdrant deletion is noted as being handled in the knowledge_indexer worker (to be implemented in Step 8).
