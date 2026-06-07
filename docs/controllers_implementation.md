# Controllers Implementation — Step 4

This document outlines the implementation plan for FastAPI controllers in the AI Sales Agent project, adapted to the current project structure with tenant logic excluded.

---

## Overview

This step implements the FastAPI controllers required for handling API requests:
- **Webhook Controller** — Handles WhatsApp webhook reception and verification
- **Conversation Controller** — Manages conversation operations
- **Knowledge Controller** — Manages knowledge base document operations
- **Lead Controller** — Manages lead operations

**Note:** Tenant-specific parameters and logic are excluded from this implementation. Tenant logic will be implemented in a later phase.

---

## Current State Analysis

### Existing Controllers

#### `app/edge/http/controller/auth_controller.py`
- Status: ✅ Exists
- Uses `@inject` decorator on `__init__`
- Uses `Provide["auth_mediator"]` for dependency injection
- Uses structlog for logging
- Has try/except blocks with logging
- Returns data directly (not wrapped in response objects)

### Controllers to Create

#### `app/edge/http/controller/webhook_controller.py`
- Status: ❌ Does not exist
- Needs: handle_whatsapp, verify_whatsapp methods

#### `app/edge/http/controller/conversation_controller.py`
- Status: ❌ Does not exist
- Needs: list_conversations, get_conversation, takeover, release methods

#### `app/edge/http/controller/knowledge_controller.py`
- Status: ❌ Does not exist
- Needs: upload, list_docs, delete_doc, reindex_doc methods

#### `app/edge/http/controller/lead_controller.py`
- Status: ❌ Does not exist
- Needs: list_leads, get_lead, update_stage methods

---

## Implementation Details

### 1. Create `app/edge/http/controller/webhook_controller.py`

Create new file with webhook controller:

```python
from app.di.container import container
from dependency_injector.wiring import inject, Provide
from fastapi import Request, BackgroundTasks, HTTPException
from fastapi.responses import PlainTextResponse
from app.mediator.message_mediator import MessageMediator
from app.schemas.webhook_schema import WhatsAppWebhookPayload, InboundMessage
from app.utils.security_util import verify_whatsapp_signature
from structlog import get_logger
import os

logger = get_logger(__name__)


class WebhookController:
    @inject
    def __init__(self, message_mediator = Provide["message_mediator"]):
        self.mediator = message_mediator

    async def handle_whatsapp(
        self,
        request: Request,
        background_tasks: BackgroundTasks,
    ):
        try:
            logger.info("WebhookController: Handling WhatsApp webhook...")

            # 1. Verify Meta HMAC-SHA256 — raises 403 if invalid
            body = await request.body()
            signature = request.headers.get("X-Hub-Signature-256", "")
            verify_whatsapp_signature(body, signature)

            # 2. Parse Meta payload
            data = await request.json()
            payload = WhatsAppWebhookPayload(**data)

            # 3. Extract each message and queue (non-blocking)
            for entry in payload.entry:
                for change in entry.changes:
                    for msg in (change.value.messages or []):
                        inbound = InboundMessage(
                            from_number=msg.from_,
                            message_id=msg.id,
                            text=msg.text.body if msg.text else None,
                            media_type=msg.type if msg.type != "text" else None,
                            media_id=(msg.audio or msg.image or {}).get("id") if msg.type != "text" else None,
                            contact_name=(change.value.contacts or [{}])[0].get("profile", {}).get("name"),
                        )
                        background_tasks.add_task(
                            self.mediator.handle_inbound,
                            message=inbound,
                            channel="whatsapp",
                        )

            # MUST return 200 fast — Meta retries if it doesn't get 200
            logger.info("WebhookController: WhatsApp webhook handled successfully.")
            return {"status": "ok"}

        except Exception as e:
            logger.error("WebhookController: Failed to handle WhatsApp webhook.", exc_info=True)
            raise e

    async def verify_whatsapp(
        self,
        mode: str,
        challenge: str,
        verify_token: str,
    ):
        try:
            logger.info("WebhookController: Verifying WhatsApp webhook...")

            # Use environment variable for verify token (tenant logic excluded)
            expected_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
            if not expected_token:
                raise HTTPException(500, "WhatsApp verify token not configured")

            if verify_token != expected_token:
                raise HTTPException(403, "Invalid verify token")

            logger.info("WebhookController: WhatsApp webhook verified successfully.")
            return PlainTextResponse(challenge)

        except HTTPException:
            raise
        except Exception as e:
            logger.error("WebhookController: Failed to verify WhatsApp webhook.", exc_info=True)
            raise e
```

**Changes from build plan:**
- Removed `tenant_id` parameter from both methods (tenant logic excluded)
- Removed `tenant_repo` dependency (tenant logic excluded)
- Removed `tenant_id` from mediator call
- Used environment variable `WHATSAPP_VERIFY_TOKEN` instead of tenant-specific token
- Added `@inject` decorator on `__init__` following project pattern
- Added try/except blocks with logging following project pattern

---

### 2. Create `app/edge/http/controller/conversation_controller.py`

Create new file with conversation controller:

```python
from app.di.container import container
from dependency_injector.wiring import inject, Provide
from app.repositories.conversation_repository import ConversationRepository
from fastapi import HTTPException
from structlog import get_logger

logger = get_logger(__name__)


class ConversationController:
    @inject
    def __init__(self, conversation_repo = Provide["conversation_repository"]):
        self.repo = conversation_repo

    async def list_conversations(self, status, channel, limit, offset):
        try:
            logger.info("ConversationController: Listing conversations...")

            conversations = await self.repo.list_all(
                status=status, channel=channel, limit=limit, offset=offset,
            )

            logger.info("ConversationController: Conversations listed successfully.")
            return {"data": conversations, "total": len(conversations)}

        except Exception as e:
            logger.error("ConversationController: Failed to list conversations.", exc_info=True)
            raise e

    async def get_conversation(self, conversation_id: str):
        try:
            logger.info(f"ConversationController: Getting conversation {conversation_id}...")

            conv = await self.repo.get_with_messages(conversation_id)
            if not conv:
                raise HTTPException(404, "Conversation not found")

            logger.info(f"ConversationController: Conversation {conversation_id} retrieved successfully.")
            return conv

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"ConversationController: Failed to get conversation {conversation_id}.", exc_info=True)
            raise e

    async def takeover(self, conversation_id: str, agent_id: str):
        """Human agent takes over — AI stops responding."""
        try:
            logger.info(f"ConversationController: Taking over conversation {conversation_id}...")

            await self.repo.update_status(conversation_id, "escalated", agent_id=agent_id)

            logger.info(f"ConversationController: Conversation {conversation_id} taken over successfully.")
            return {"message": "Conversation assigned to you. AI has paused."}

        except Exception as e:
            logger.error(f"ConversationController: Failed to take over conversation {conversation_id}.", exc_info=True)
            raise e

    async def release(self, conversation_id: str):
        """Return conversation to AI."""
        try:
            logger.info(f"ConversationController: Releasing conversation {conversation_id}...")

            await self.repo.update_status(conversation_id, "active", agent_id=None)

            logger.info(f"ConversationController: Conversation {conversation_id} released successfully.")
            return {"message": "AI has resumed handling this conversation."}

        except Exception as e:
            logger.error(f"ConversationController: Failed to release conversation {conversation_id}.", exc_info=True)
            raise e
```

**Changes from build plan:**
- Removed `tenant_id` parameter from `list_conversations` method (tenant logic excluded)
- Changed `list_by_tenant` to `list_all` in repository call
- Added `@inject` decorator on `__init__` following project pattern
- Added try/except blocks with logging following project pattern

---

### 3. Create `app/edge/http/controller/knowledge_controller.py`

Create new file with knowledge controller:

```python
from app.di.container import container
from dependency_injector.wiring import inject, Provide
from fastapi import UploadFile, HTTPException
from app.repositories.knowledge_repository import KnowledgeRepository
from app.mediator.knowledge_mediator import KnowledgeMediator
from structlog import get_logger

logger = get_logger(__name__)

ALLOWED_TYPES = {"pdf", "docx", "txt", "csv"}


class KnowledgeController:
    @inject
    def __init__(
        self,
        knowledge_repo = Provide["knowledge_repository"],
        knowledge_mediator = Provide["knowledge_mediator"],
    ):
        self.repo = knowledge_repo
        self.mediator = knowledge_mediator

    async def upload(self, file: UploadFile):
        try:
            logger.info(f"KnowledgeController: Uploading document {file.filename}...")

            ext = file.filename.split(".")[-1].lower()
            if ext not in ALLOWED_TYPES:
                raise HTTPException(400, f"File type .{ext} not supported. Allowed: {ALLOWED_TYPES}")

            doc = await self.mediator.ingest_document(file=file, file_type=ext)

            logger.info(f"KnowledgeController: Document {file.filename} uploaded successfully.")
            return {"message": "Document uploaded and indexing started.", "doc_id": str(doc.id)}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"KnowledgeController: Failed to upload document {file.filename}.", exc_info=True)
            raise e

    async def list_docs(self):
        try:
            logger.info("KnowledgeController: Listing documents...")

            docs = await self.repo.list_all()

            logger.info("KnowledgeController: Documents listed successfully.")
            return docs

        except Exception as e:
            logger.error("KnowledgeController: Failed to list documents.", exc_info=True)
            raise e

    async def delete_doc(self, doc_id: str):
        try:
            logger.info(f"KnowledgeController: Deleting document {doc_id}...")

            await self.mediator.delete_document(doc_id)

            logger.info(f"KnowledgeController: Document {doc_id} deleted successfully.")
            return {"message": "Document deleted and removed from knowledge base."}

        except Exception as e:
            logger.error(f"KnowledgeController: Failed to delete document {doc_id}.", exc_info=True)
            raise e

    async def reindex_doc(self, doc_id: str):
        try:
            logger.info(f"KnowledgeController: Reindexing document {doc_id}...")

            await self.mediator.reindex_document(doc_id)

            logger.info(f"KnowledgeController: Document {doc_id} reindexing started.")
            return {"message": "Reindexing started."}

        except Exception as e:
            logger.error(f"KnowledgeController: Failed to reindex document {doc_id}.", exc_info=True)
            raise e
```

**Changes from build plan:**
- Removed `tenant_id` parameter from `upload` and `list_docs` methods (tenant logic excluded)
- Removed `tenant_id` from mediator call
- Changed `list_by_tenant` to `list_all` in repository call
- Added `@inject` decorator on `__init__` following project pattern
- Added try/except blocks with logging following project pattern

---

### 4. Create `app/edge/http/controller/lead_controller.py`

Create new file with lead controller:

```python
from app.di.container import container
from dependency_injector.wiring import inject, Provide
from app.repositories.lead_repository import LeadRepository
from fastapi import HTTPException
from structlog import get_logger

logger = get_logger(__name__)


class LeadController:
    @inject
    def __init__(self, lead_repo = Provide["lead_repository"]):
        self.repo = lead_repo

    async def list_leads(self, stage, limit, offset):
        try:
            logger.info("LeadController: Listing leads...")

            leads = await self.repo.list_all(stage=stage, limit=limit, offset=offset)

            logger.info("LeadController: Leads listed successfully.")
            return {"data": leads, "total": len(leads)}

        except Exception as e:
            logger.error("LeadController: Failed to list leads.", exc_info=True)
            raise e

    async def get_lead(self, lead_id: str):
        try:
            logger.info(f"LeadController: Getting lead {lead_id}...")

            lead = await self.repo.get_by_id(lead_id)
            if not lead:
                raise HTTPException(404, "Lead not found")

            logger.info(f"LeadController: Lead {lead_id} retrieved successfully.")
            return lead

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"LeadController: Failed to get lead {lead_id}.", exc_info=True)
            raise e

    async def update_stage(self, lead_id: str, stage: str):
        try:
            logger.info(f"LeadController: Updating lead {lead_id} stage to {stage}...")

            valid_stages = {"cold", "warm", "hot", "qualified", "converted"}
            if stage not in valid_stages:
                raise HTTPException(400, f"Invalid stage. Choose from: {valid_stages}")

            await self.repo.update_stage(lead_id, stage)

            logger.info(f"LeadController: Lead {lead_id} stage updated to {stage} successfully.")
            return {"message": f"Lead stage updated to {stage}"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"LeadController: Failed to update lead {lead_id} stage.", exc_info=True)
            raise e
```

**Changes from build plan:**
- Removed `tenant_id` parameter from `list_leads` method (tenant logic excluded)
- Changed `list_by_tenant` to `list_all` in repository call
- Added `@inject` decorator on `__init__` following project pattern
- Added try/except blocks with logging following project pattern

---

## Implementation Checklist

- [ ] Create `app/edge/http/controller/webhook_controller.py`
  - [ ] Create handle_whatsapp method
  - [ ] Create verify_whatsapp method
- [ ] Create `app/edge/http/controller/conversation_controller.py`
  - [ ] Create list_conversations method
  - [ ] Create get_conversation method
  - [ ] Create takeover method
  - [ ] Create release method
- [ ] Create `app/edge/http/controller/knowledge_controller.py`
  - [ ] Create upload method
  - [ ] Create list_docs method
  - [ ] Create delete_doc method
  - [ ] Create reindex_doc method
- [ ] Create `app/edge/http/controller/lead_controller.py`
  - [ ] Create list_leads method
  - [ ] Create get_lead method
  - [ ] Create update_stage method

---

## Notes

- **Tenant logic excluded** — All `tenant_id` parameters have been removed from controller methods. Tenant logic will be implemented in a later phase.
- **Project structure preserved** — All controllers follow the existing pattern of using `@inject` decorator on `__init__`, `Provide["xxx"]` for dependency injection, structlog for logging, and try/except blocks with logging.
- **Repository method changes** — Changed `list_by_tenant` to `list_all` in repository calls since tenant logic is excluded.
- **Webhook verify token** — Uses environment variable `WHATSAPP_VERIFY_TOKEN` instead of tenant-specific token since tenant logic is excluded.
- **Mediator dependencies** — Controllers depend on mediators and repositories which will be implemented in later steps.
