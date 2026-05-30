# Mediators Implementation — Step 5

This document outlines the implementation plan for mediators in the AI Sales Agent project, adapted to the current project structure with tenant logic excluded.

---

## Overview

This step implements the mediators required for coordinating between controllers and services:
- **MessageMediator** — Handles inbound message processing and coordinates conversation/lead creation
- **KnowledgeMediator** — Handles knowledge document ingestion and indexing

**Note:** Tenant-specific parameters and logic are excluded from this implementation. Tenant logic will be implemented in a later phase.

---

## Current State Analysis

### Existing Mediators

#### `app/mediator/auth_mediator.py`
- Status: ✅ Exists
- Uses `@inject` decorator on `__init__`
- Uses `Provide["auth_service"]` for dependency injection
- Uses structlog for logging
- Has try/except blocks with logging
- Returns data directly (not wrapped in response objects)

### Mediators to Create

#### `app/mediator/message_mediator.py`
- Status: ❌ Does not exist
- Needs: handle_inbound method

#### `app/mediator/knowledge_mediator.py`
- Status: ❌ Does not exist
- Needs: ingest_document, delete_document, reindex_document methods

---

## Implementation Details

### 1. Create `app/mediator/message_mediator.py`

Create new file with message mediator:

```python
from app.di.container import container
from dependency_injector.wiring import inject, Provide
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.lead_repository import LeadRepository
from app.schemas.webhook_schema import InboundMessage
from app.configs.messaging_config import RabbitMQClient
from structlog import get_logger

logger = get_logger(__name__)


class MessageMediator:
    @inject
    def __init__(
        self,
        conversation_repo = Provide["conversation_repository"],
        lead_repo = Provide["lead_repository"],
        rabbitmq = Provide["rabbitmq"],
    ):
        self.conv_repo = conversation_repo
        self.lead_repo = lead_repo
        self.rabbitmq = rabbitmq

    async def handle_inbound(
        self,
        message: InboundMessage,
        channel: str,
    ) -> None:
        try:
            logger.info("MessageMediator: Handling inbound message...")

            # 1. Get or create conversation
            conversation = await self.conv_repo.get_or_create(
                customer_phone=message.from_number,
                channel=channel,
                customer_name=message.contact_name,
            )

            # 2. Persist raw customer message
            await self.conv_repo.add_message(
                conversation_id=str(conversation.id),
                role="user",
                content=message.text or "",
                media_type=message.media_type,
            )

            # 3. Skip AI if a human agent is handling this conversation
            if conversation.status == "escalated":
                logger.info(f"MessageMediator: Skipping AI — conv {conversation.id} is escalated to human")
                return

            # 4. Get or create lead record
            lead = await self.lead_repo.get_or_create(
                conversation_id=str(conversation.id),
                customer_phone=message.from_number,
            )

            # 5. Publish to RabbitMQ ai.messages queue — non-blocking
            await self.rabbitmq.publish(
                exchange   = "ai",
                routing_key = "ai.messages",
                message    = dict(
                    conversation_id = str(conversation.id),
                    lead_id         = str(lead.id),
                    message_text    = message.text or "",
                    media_type      = message.media_type,
                    media_id        = message.media_id,
                    channel         = channel,
                ),
            )

            logger.info(f"MessageMediator: Queued AI task for conversation {conversation.id}")

        except Exception as e:
            logger.error("MessageMediator: Failed to handle inbound message.", exc_info=True)
            raise e
```

**Changes from build plan:**
- Removed `tenant_id` parameter from `handle_inbound` method (tenant logic excluded)
- Removed `tenant_repo` dependency (tenant logic excluded)
- Removed `tenant_id` from repository calls
- Removed `tenant_id` from RabbitMQ message
- Changed from Celery `process_message_task.delay()` to RabbitMQ `rabbitmq.publish()`
- Added `rabbitmq` dependency injection
- Added `@inject` decorator on `__init__` following project pattern
- Added try/except blocks with logging following project pattern
- Changed from `logging` to `structlog`

---

### 2. Create `app/mediator/knowledge_mediator.py`

Create new file with knowledge mediator:

```python
from app.di.container import container
from dependency_injector.wiring import inject, Provide
from fastapi import UploadFile
from app.repositories.knowledge_repository import KnowledgeRepository
from app.configs.messaging_config import RabbitMQClient
from app.utils.storage_util import upload_to_s3
from structlog import get_logger

logger = get_logger(__name__)


class KnowledgeMediator:
    @inject
    def __init__(
        self,
        knowledge_repo = Provide["knowledge_repository"],
        rabbitmq = Provide["rabbitmq"],
    ):
        self.repo = knowledge_repo
        self.rabbitmq = rabbitmq

    async def ingest_document(self, file: UploadFile, file_type: str):
        try:
            logger.info(f"KnowledgeMediator: Ingesting document {file.filename}...")

            # 1. Upload raw file to S3
            file_bytes = await file.read()
            file_url = await upload_to_s3(file_bytes, file.filename)

            # 2. Create DB record (status=pending)
            doc = await self.repo.create(
                filename=file.filename,
                file_type=file_type,
                file_url=file_url,
            )

            # 3. Publish to RabbitMQ indexing queue
            await self.rabbitmq.publish(
                exchange    = "ai",
                routing_key = "ai.knowledge",
                message     = dict(
                    doc_id    = str(doc.id),
                    file_url  = file_url,
                    file_type = file_type,
                ),
            )

            logger.info(f"KnowledgeMediator: Document {file.filename} ingested successfully.")
            return doc

        except Exception as e:
            logger.error(f"KnowledgeMediator: Failed to ingest document {file.filename}.", exc_info=True)
            raise e

    async def delete_document(self, doc_id: str):
        try:
            logger.info(f"KnowledgeMediator: Deleting document {doc_id}...")

            doc = await self.repo.get_by_id(doc_id)
            # Remove from Qdrant (by doc_id metadata filter)
            await self.repo.delete_qdrant_chunks(doc_id)
            # Delete DB record
            await self.repo.delete(doc_id)

            logger.info(f"KnowledgeMediator: Document {doc_id} deleted successfully.")

        except Exception as e:
            logger.error(f"KnowledgeMediator: Failed to delete document {doc_id}.", exc_info=True)
            raise e

    async def reindex_document(self, doc_id: str):
        try:
            logger.info(f"KnowledgeMediator: Reindexing document {doc_id}...")

            doc = await self.repo.get_by_id(doc_id)
            await self.repo.update_status(doc_id, "pending")
            await self.rabbitmq.publish(
                exchange    = "ai",
                routing_key = "ai.knowledge",
                message     = dict(
                    doc_id    = doc_id,
                    file_url  = doc.file_url,
                    file_type = doc.file_type,
                ),
            )

            logger.info(f"KnowledgeMediator: Document {doc_id} reindexing started.")

        except Exception as e:
            logger.error(f"KnowledgeMediator: Failed to reindex document {doc_id}.", exc_info=True)
            raise e
```

**Changes from build plan:**
- Removed `tenant_id` parameter from `ingest_document` method (tenant logic excluded)
- Removed `tenant_id` from `upload_to_s3` call
- Removed `tenant_id` from repository `create` call
- Removed `tenant_id` from RabbitMQ message
- Changed from Celery `index_document_task.delay()` to RabbitMQ `rabbitmq.publish()`
- Removed `tenant_id` parameter from `delete_qdrant_chunks` call
- Changed from Celery `index_document_task.delay()` to RabbitMQ `rabbitmq.publish()` in `reindex_document`
- Added `rabbitmq` dependency injection
- Added `@inject` decorator on `__init__` following project pattern
- Added try/except blocks with logging following project pattern
- Changed from `logging` to `structlog`

---

### 3. Update `app/mediator/__init__.py`

Add imports for the new mediators (if file exists, otherwise create it):

```python
from app.mediator.auth_mediator import AuthMediator
from app.mediator.message_mediator import MessageMediator
from app.mediator.knowledge_mediator import KnowledgeMediator

__all__ = [
    "AuthMediator",
    "MessageMediator",
    "KnowledgeMediator",
]
```

**Note:** Check if `__init__.py` exists in the mediator directory. If not, create it with the above content.

---

## Implementation Checklist

- [ ] Create `app/mediator/message_mediator.py`
  - [ ] Create handle_inbound method
  - [ ] Remove tenant_id parameters
  - [ ] Add proper imports and logging
- [ ] Create `app/mediator/knowledge_mediator.py`
  - [ ] Create ingest_document method
  - [ ] Create delete_document method
  - [ ] Create reindex_document method
  - [ ] Remove tenant_id parameters
  - [ ] Add proper imports and logging
- [ ] Update/Create `app/mediator/__init__.py`
  - [ ] Add imports for new mediators
  - [ ] Update `__all__` list

---

## Notes

- **Tenant logic excluded** — All `tenant_id` parameters have been removed from mediator methods. Tenant logic will be implemented in a later phase.
- **Project structure preserved** — All mediators follow the existing pattern of using `@inject` decorator on `__init__`, `Provide["xxx"]` for dependency injection, structlog for logging, and try/except blocks with logging.
- **Repository method changes** — Repository calls no longer include `tenant_id` since tenant logic is excluded.
- **Celery task changes** — Celery task calls no longer include `tenant_id` since tenant logic is excluded.
- **Storage changes** — `upload_to_s3` call no longer includes `tenant_id` since tenant logic is excluded.
- **Worker dependencies** — Mediators depend on workers (`process_message_task`, `index_document_task`) which will be implemented in later steps.
- **Repository dependencies** — Mediators depend on repositories which will be implemented in later steps.
- **Utility dependencies** — KnowledgeMediator depends on `upload_to_s3` utility which will be implemented in later steps.
