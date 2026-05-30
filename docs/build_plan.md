# AI Sales Agent — Step-by-Step Build Plan
> Flow: `schema → route → controller → mediator → service → repository`  
> Stack: FastAPI Boilerplate · PostgreSQL · Redis · Qdrant · RabbitMQ · OpenAI

---

# PHASE 1 — MVP (WhatsApp + AI Agent)

---

## Step 1 — Models

### `app/models/tenant_model.py`
```python
from sqlalchemy import String, Boolean, JSON, Text, Integer
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.models.base_model import BaseModel


class Tenant(BaseModel):
    __tablename__ = "tenants"

    name:                   Mapped[str]        = mapped_column(String(200))
    slug:                   Mapped[str]        = mapped_column(String(100), unique=True, index=True)
    plan:                   Mapped[str]        = mapped_column(String(50), default="free")
    is_active:              Mapped[bool]       = mapped_column(Boolean, default=True)

    # AI persona
    ai_persona_name:        Mapped[str]        = mapped_column(String(100), default="Assistant")
    ai_config:              Mapped[dict]       = mapped_column(JSON, default=dict)
    system_prompt_override: Mapped[str | None] = mapped_column(Text, nullable=True)

    # WhatsApp
    whatsapp_phone_id:      Mapped[str | None] = mapped_column(String(100), nullable=True)
    whatsapp_access_token:  Mapped[str | None] = mapped_column(Text, nullable=True)
    whatsapp_verify_token:  Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Usage counters
    monthly_message_count:  Mapped[int]        = mapped_column(Integer, default=0)
    monthly_token_count:    Mapped[int]        = mapped_column(Integer, default=0)
```

---

### `app/models/conversation_model.py`
```python
import uuid
from sqlalchemy import String, ForeignKey, Text, JSON
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.models.base_model import BaseModel


class Conversation(BaseModel):
    __tablename__ = "conversations"

    tenant_id:         Mapped[uuid.UUID]       = mapped_column(ForeignKey("tenants.id"), index=True)
    channel:           Mapped[str]             = mapped_column(String(50))
    # whatsapp | instagram | facebook | web

    customer_phone:    Mapped[str]             = mapped_column(String(50), index=True)
    customer_name:     Mapped[str | None]      = mapped_column(String(200), nullable=True)
    customer_email:    Mapped[str | None]      = mapped_column(String(200), nullable=True)

    status:            Mapped[str]             = mapped_column(String(50), default="active")
    # active | escalated | resolved | closed

    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    meta:              Mapped[dict]             = mapped_column(JSON, default=dict)
    # stores: detected_language, last_intent, ai_confidence

    messages:          Mapped[list]             = relationship("Message", back_populates="conversation")
```

---

### `app/models/message_model.py`
```python
import uuid
from sqlalchemy import String, ForeignKey, Text, Integer
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.models.base_model import BaseModel


class Message(BaseModel):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID]      = mapped_column(ForeignKey("conversations.id"), index=True)
    tenant_id:       Mapped[uuid.UUID]      = mapped_column(ForeignKey("tenants.id"), index=True)

    role:            Mapped[str]            = mapped_column(String(20))
    # user | assistant | system

    content:         Mapped[str]            = mapped_column(Text)
    media_type:      Mapped[str | None]     = mapped_column(String(50), nullable=True)
    # text | image | audio | document
    media_url:       Mapped[str | None]     = mapped_column(String(500), nullable=True)

    tokens_used:     Mapped[int | None]     = mapped_column(Integer, nullable=True)
    latency_ms:      Mapped[int | None]     = mapped_column(Integer, nullable=True)

    conversation:    Mapped["Conversation"] = relationship(back_populates="messages")
```

---

### `app/models/lead_model.py`
```python
import uuid
from sqlalchemy import String, ForeignKey, Integer, JSON
from sqlalchemy.orm import mapped_column, Mapped
from app.models.base_model import BaseModel


class Lead(BaseModel):
    __tablename__ = "leads"

    tenant_id:           Mapped[uuid.UUID]  = mapped_column(ForeignKey("tenants.id"), index=True)
    conversation_id:     Mapped[uuid.UUID]  = mapped_column(ForeignKey("conversations.id"))

    customer_phone:      Mapped[str]        = mapped_column(String(50), index=True)
    customer_name:       Mapped[str | None] = mapped_column(String(200), nullable=True)
    customer_email:      Mapped[str | None] = mapped_column(String(200), nullable=True)

    score:               Mapped[int]        = mapped_column(Integer, default=0)
    # 0–100

    stage:               Mapped[str]        = mapped_column(String(50), default="cold")
    # cold | warm | hot | qualified | converted

    qualification_data:  Mapped[dict]       = mapped_column(JSON, default=dict)
    # {"budget": "50k", "timeline": "next month", "needs": [...]}
```

---

### `app/models/knowledge_doc_model.py`
```python
import uuid
from sqlalchemy import String, ForeignKey, Integer
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.models.base_model import BaseModel


class KnowledgeDoc(BaseModel):
    __tablename__ = "knowledge_docs"

    tenant_id:   Mapped[uuid.UUID]  = mapped_column(ForeignKey("tenants.id"), index=True)
    filename:    Mapped[str]        = mapped_column(String(300))
    file_type:   Mapped[str]        = mapped_column(String(20))
    # pdf | docx | txt | csv
    file_url:    Mapped[str]        = mapped_column(String(500))
    status:      Mapped[str]        = mapped_column(String(50), default="pending")
    # pending | processing | indexed | failed
    chunk_count: Mapped[int]        = mapped_column(Integer, default=0)

    chunks:      Mapped[list]       = relationship("KnowledgeChunk", back_populates="doc")


class KnowledgeChunk(BaseModel):
    __tablename__ = "knowledge_chunks"

    doc_id:         Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_docs.id"), index=True)
    tenant_id:      Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    content:        Mapped[str]       = mapped_column(Text)
    qdrant_point_id:Mapped[str]       = mapped_column(String(100))

    doc: Mapped["KnowledgeDoc"] = relationship(back_populates="chunks")
```

---

### Run Migrations
```bash
alembic revision --autogenerate -m "add_tenant_model"
alembic revision --autogenerate -m "add_conversation_message_models"
alembic revision --autogenerate -m "add_lead_model"
alembic revision --autogenerate -m "add_knowledge_models"
alembic upgrade head
```

---

## Step 2 — Schemas

### `app/schemas/tenant_schema.py`
```python
from pydantic import BaseModel as PydanticBase
from typing import Optional
import uuid


class TenantCreate(PydanticBase):
    name: str
    slug: str
    plan: str = "free"
    ai_persona_name: str = "Assistant"


class TenantUpdate(PydanticBase):
    ai_persona_name: Optional[str] = None
    ai_config: Optional[dict] = None
    system_prompt_override: Optional[str] = None
    whatsapp_phone_id: Optional[str] = None
    whatsapp_access_token: Optional[str] = None
    whatsapp_verify_token: Optional[str] = None


class TenantResponse(PydanticBase):
    id: uuid.UUID
    name: str
    slug: str
    plan: str
    is_active: bool
    ai_persona_name: str

    class Config:
        from_attributes = True
```

---

### `app/schemas/webhook_schema.py`
```python
from pydantic import BaseModel as PydanticBase
from typing import Optional, List


# ── WhatsApp Cloud API payload structure ──────────────────────────

class WhatsAppTextMessage(PydanticBase):
    body: str


class WhatsAppAudio(PydanticBase):
    id: str
    mime_type: Optional[str] = None


class WhatsAppImage(PydanticBase):
    id: str
    mime_type: Optional[str] = None


class WhatsAppMessage(PydanticBase):
    id: str
    from_: str
    timestamp: str
    type: str                              # text | audio | image | document
    text: Optional[WhatsAppTextMessage] = None
    audio: Optional[WhatsAppAudio] = None
    image: Optional[WhatsAppImage] = None

    class Config:
        populate_by_name = True
        fields = {"from_": "from"}


class WhatsAppContact(PydanticBase):
    profile: Optional[dict] = None
    wa_id: Optional[str] = None


class WhatsAppValue(PydanticBase):
    messaging_product: str
    metadata: Optional[dict] = None
    messages: Optional[List[WhatsAppMessage]] = None
    contacts: Optional[List[WhatsAppContact]] = None


class WhatsAppChange(PydanticBase):
    value: WhatsAppValue
    field: str


class WhatsAppEntry(PydanticBase):
    id: str
    changes: List[WhatsAppChange]


class WhatsAppWebhookPayload(PydanticBase):
    object: str
    entry: List[WhatsAppEntry]


# ── Normalised inbound message (channel-agnostic) ────────────────

class InboundMessage(PydanticBase):
    from_number: str
    message_id: str
    text: Optional[str] = None
    media_type: Optional[str] = None       # audio | image | document
    media_id: Optional[str] = None         # Meta media ID to download
    contact_name: Optional[str] = None
```

---

### `app/schemas/conversation_schema.py`
```python
from pydantic import BaseModel as PydanticBase
from typing import Optional, List
import uuid
from datetime import datetime


class MessageResponse(PydanticBase):
    id: uuid.UUID
    role: str
    content: str
    media_type: Optional[str] = None
    tokens_used: Optional[int] = None
    latency_ms: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(PydanticBase):
    id: uuid.UUID
    channel: str
    customer_phone: str
    customer_name: Optional[str] = None
    status: str
    created_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True


class ConversationListResponse(PydanticBase):
    id: uuid.UUID
    channel: str
    customer_phone: str
    customer_name: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class TakeoverRequest(PydanticBase):
    agent_id: uuid.UUID
```

---

### `app/schemas/knowledge_schema.py`
```python
from pydantic import BaseModel as PydanticBase
from typing import Optional
import uuid
from datetime import datetime


class KnowledgeDocResponse(PydanticBase):
    id: uuid.UUID
    filename: str
    file_type: str
    status: str
    chunk_count: int
    created_at: datetime

    class Config:
        from_attributes = True
```

---

### `app/schemas/lead_schema.py`
```python
from pydantic import BaseModel as PydanticBase
from typing import Optional
import uuid
from datetime import datetime


class LeadResponse(PydanticBase):
    id: uuid.UUID
    customer_phone: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    score: int
    stage: str
    qualification_data: dict
    created_at: datetime

    class Config:
        from_attributes = True


class LeadStageUpdate(PydanticBase):
    stage: str
    # cold | warm | hot | qualified | converted
```

---

## Step 3 — Routes

### `app/edge/http/routes/webhook_route.py`
```python
from fastapi import APIRouter, Request, BackgroundTasks, Query, Depends
from app.di.container import Container
from dependency_injector.wiring import inject, Provide

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/whatsapp/{tenant_id}")
@inject
async def receive_whatsapp(
    tenant_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    controller=Provide[Container.webhook_controller],
):
    return await controller.handle_whatsapp(tenant_id, request, background_tasks)


@router.get("/whatsapp/{tenant_id}")
@inject
async def verify_whatsapp(
    tenant_id: str,
    hub_mode: str       = Query(alias="hub.mode"),
    hub_challenge: str  = Query(alias="hub.challenge"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    controller=Provide[Container.webhook_controller],
):
    return await controller.verify_whatsapp(tenant_id, hub_mode, hub_challenge, hub_verify_token)
```

---

### `app/edge/http/routes/conversation_route.py`
```python
from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.di.container import Container
from dependency_injector.wiring import inject, Provide

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("/")
@inject
async def list_conversations(
    tenant_id: str,
    status: Optional[str]  = Query(None),
    channel: Optional[str] = Query(None),
    limit: int             = Query(50, le=100),
    offset: int            = Query(0),
    controller=Provide[Container.conversation_controller],
):
    return await controller.list_conversations(tenant_id, status, channel, limit, offset)


@router.get("/{conversation_id}")
@inject
async def get_conversation(
    conversation_id: str,
    controller=Provide[Container.conversation_controller],
):
    return await controller.get_conversation(conversation_id)


@router.post("/{conversation_id}/takeover")
@inject
async def takeover(
    conversation_id: str,
    body: TakeoverRequest,
    controller=Provide[Container.conversation_controller],
):
    return await controller.takeover(conversation_id, str(body.agent_id))


@router.post("/{conversation_id}/release")
@inject
async def release(
    conversation_id: str,
    controller=Provide[Container.conversation_controller],
):
    return await controller.release(conversation_id)
```

---

### `app/edge/http/routes/knowledge_route.py`
```python
from fastapi import APIRouter, UploadFile, File, Depends
from app.di.container import Container
from dependency_injector.wiring import inject, Provide

router = APIRouter(prefix="/knowledge", tags=["Knowledge"])


@router.post("/upload")
@inject
async def upload_document(
    tenant_id: str,
    file: UploadFile = File(...),
    controller=Provide[Container.knowledge_controller],
):
    return await controller.upload(tenant_id, file)


@router.get("/docs")
@inject
async def list_docs(
    tenant_id: str,
    controller=Provide[Container.knowledge_controller],
):
    return await controller.list_docs(tenant_id)


@router.delete("/docs/{doc_id}")
@inject
async def delete_doc(
    doc_id: str,
    controller=Provide[Container.knowledge_controller],
):
    return await controller.delete_doc(doc_id)


@router.post("/docs/{doc_id}/reindex")
@inject
async def reindex_doc(
    doc_id: str,
    controller=Provide[Container.knowledge_controller],
):
    return await controller.reindex_doc(doc_id)
```

---

### `app/edge/http/routes/lead_route.py`
```python
from fastapi import APIRouter, Query
from typing import Optional
from app.di.container import Container
from dependency_injector.wiring import inject, Provide
from app.schemas.lead_schema import LeadStageUpdate

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.get("/")
@inject
async def list_leads(
    tenant_id: str,
    stage: Optional[str] = Query(None),
    limit: int           = Query(50, le=100),
    offset: int          = Query(0),
    controller=Provide[Container.lead_controller],
):
    return await controller.list_leads(tenant_id, stage, limit, offset)


@router.get("/{lead_id}")
@inject
async def get_lead(
    lead_id: str,
    controller=Provide[Container.lead_controller],
):
    return await controller.get_lead(lead_id)


@router.patch("/{lead_id}/stage")
@inject
async def update_stage(
    lead_id: str,
    body: LeadStageUpdate,
    controller=Provide[Container.lead_controller],
):
    return await controller.update_stage(lead_id, body.stage)
```

---

## Step 4 — Controllers

### `app/edge/http/controller/webhook_controller.py`
```python
from fastapi import Request, BackgroundTasks, HTTPException
from fastapi.responses import PlainTextResponse
from app.mediator.message_mediator import MessageMediator
from app.repositories.tenant_repository import TenantRepository
from app.schemas.webhook_schema import WhatsAppWebhookPayload, InboundMessage
from app.utils.security_util import verify_whatsapp_signature
import logging

logger = logging.getLogger(__name__)


class WebhookController:
    def __init__(
        self,
        message_mediator: MessageMediator,
        tenant_repo: TenantRepository,
    ):
        self.mediator    = message_mediator
        self.tenant_repo = tenant_repo

    async def handle_whatsapp(
        self,
        tenant_id: str,
        request: Request,
        background_tasks: BackgroundTasks,
    ):
        # 1. Verify Meta HMAC-SHA256 — raises 403 if invalid
        body      = await request.body()
        signature = request.headers.get("X-Hub-Signature-256", "")
        verify_whatsapp_signature(body, signature)

        # 2. Parse Meta payload
        data    = await request.json()
        payload = WhatsAppWebhookPayload(**data)

        # 3. Extract each message and queue (non-blocking)
        for entry in payload.entry:
            for change in entry.changes:
                for msg in (change.value.messages or []):
                    inbound = InboundMessage(
                        from_number  = msg.from_,
                        message_id   = msg.id,
                        text         = msg.text.body if msg.text else None,
                        media_type   = msg.type if msg.type != "text" else None,
                        media_id     = (msg.audio or msg.image or {}).get("id") if msg.type != "text" else None,
                        contact_name = (change.value.contacts or [{}])[0].get("profile", {}).get("name"),
                    )
                    background_tasks.add_task(
                        self.mediator.handle_inbound,
                        tenant_id=tenant_id,
                        message=inbound,
                        channel="whatsapp",
                    )

        # MUST return 200 fast — Meta retries if it doesn't get 200
        return {"status": "ok"}

    async def verify_whatsapp(
        self,
        tenant_id: str,
        mode: str,
        challenge: str,
        verify_token: str,
    ):
        tenant = await self.tenant_repo.get_by_id(tenant_id)
        if not tenant:
            raise HTTPException(404, "Tenant not found")
        if verify_token != tenant.whatsapp_verify_token:
            raise HTTPException(403, "Invalid verify token")
        return PlainTextResponse(challenge)
```

---

### `app/edge/http/controller/conversation_controller.py`
```python
from app.repositories.conversation_repository import ConversationRepository
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class ConversationController:
    def __init__(self, conversation_repo: ConversationRepository):
        self.repo = conversation_repo

    async def list_conversations(self, tenant_id, status, channel, limit, offset):
        conversations = await self.repo.list_by_tenant(
            tenant_id=tenant_id, status=status, channel=channel,
            limit=limit, offset=offset,
        )
        return {"data": conversations, "total": len(conversations)}

    async def get_conversation(self, conversation_id: str):
        conv = await self.repo.get_with_messages(conversation_id)
        if not conv:
            raise HTTPException(404, "Conversation not found")
        return conv

    async def takeover(self, conversation_id: str, agent_id: str):
        """Human agent takes over — AI stops responding."""
        await self.repo.update_status(conversation_id, "escalated", agent_id=agent_id)
        return {"message": "Conversation assigned to you. AI has paused."}

    async def release(self, conversation_id: str):
        """Return conversation to AI."""
        await self.repo.update_status(conversation_id, "active", agent_id=None)
        return {"message": "AI has resumed handling this conversation."}
```

---

### `app/edge/http/controller/knowledge_controller.py`
```python
from fastapi import UploadFile, HTTPException
from app.repositories.knowledge_repository import KnowledgeRepository
from app.mediator.knowledge_mediator import KnowledgeMediator
import logging

logger = logging.getLogger(__name__)

ALLOWED_TYPES = {"pdf", "docx", "txt", "csv"}


class KnowledgeController:
    def __init__(
        self,
        knowledge_repo: KnowledgeRepository,
        knowledge_mediator: KnowledgeMediator,
    ):
        self.repo     = knowledge_repo
        self.mediator = knowledge_mediator

    async def upload(self, tenant_id: str, file: UploadFile):
        ext = file.filename.split(".")[-1].lower()
        if ext not in ALLOWED_TYPES:
            raise HTTPException(400, f"File type .{ext} not supported. Allowed: {ALLOWED_TYPES}")

        doc = await self.mediator.ingest_document(
            tenant_id=tenant_id, file=file, file_type=ext,
        )
        return {"message": "Document uploaded and indexing started.", "doc_id": str(doc.id)}

    async def list_docs(self, tenant_id: str):
        return await self.repo.list_by_tenant(tenant_id)

    async def delete_doc(self, doc_id: str):
        await self.mediator.delete_document(doc_id)
        return {"message": "Document deleted and removed from knowledge base."}

    async def reindex_doc(self, doc_id: str):
        await self.mediator.reindex_document(doc_id)
        return {"message": "Reindexing started."}
```

---

### `app/edge/http/controller/lead_controller.py`
```python
from app.repositories.lead_repository import LeadRepository
from fastapi import HTTPException


class LeadController:
    def __init__(self, lead_repo: LeadRepository):
        self.repo = lead_repo

    async def list_leads(self, tenant_id, stage, limit, offset):
        leads = await self.repo.list_by_tenant(
            tenant_id=tenant_id, stage=stage, limit=limit, offset=offset,
        )
        return {"data": leads, "total": len(leads)}

    async def get_lead(self, lead_id: str):
        lead = await self.repo.get_by_id(lead_id)
        if not lead:
            raise HTTPException(404, "Lead not found")
        return lead

    async def update_stage(self, lead_id: str, stage: str):
        valid_stages = {"cold", "warm", "hot", "qualified", "converted"}
        if stage not in valid_stages:
            raise HTTPException(400, f"Invalid stage. Choose from: {valid_stages}")
        await self.repo.update_stage(lead_id, stage)
        return {"message": f"Lead stage updated to {stage}"}
```

---

## Step 5 — Mediators

### `app/mediator/message_mediator.py`
```python
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.tenant_repository import TenantRepository
from app.repositories.lead_repository import LeadRepository
from app.schemas.webhook_schema import InboundMessage
from app.workers.message_processor import process_message_task
import logging

logger = logging.getLogger(__name__)


class MessageMediator:
    def __init__(
        self,
        conversation_repo: ConversationRepository,
        tenant_repo: TenantRepository,
        lead_repo: LeadRepository,
    ):
        self.conv_repo   = conversation_repo
        self.tenant_repo = tenant_repo
        self.lead_repo   = lead_repo

    async def handle_inbound(
        self,
        tenant_id: str,
        message: InboundMessage,
        channel: str,
    ) -> None:
        # 1. Get or create conversation
        conversation = await self.conv_repo.get_or_create(
            tenant_id=tenant_id,
            customer_phone=message.from_number,
            channel=channel,
            customer_name=message.contact_name,
        )

        # 2. Persist raw customer message
        await self.conv_repo.add_message(
            conversation_id=str(conversation.id),
            tenant_id=tenant_id,
            role="user",
            content=message.text or "",
            media_type=message.media_type,
        )

        # 3. Skip AI if a human agent is handling this conversation
        if conversation.status == "escalated":
            logger.info(f"Skipping AI — conv {conversation.id} is escalated to human")
            return

        # 4. Get or create lead record
        lead = await self.lead_repo.get_or_create(
            tenant_id=tenant_id,
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
                tenant_id       = tenant_id,
                message_text    = message.text or "",
                media_type      = message.media_type,
                media_id        = message.media_id,
                channel         = channel,
            ),
        )

        logger.info(f"Queued AI task for conversation {conversation.id}")
```

---

### `app/mediator/knowledge_mediator.py`
```python
from fastapi import UploadFile
from app.repositories.knowledge_repository import KnowledgeRepository
from app.workers.knowledge_indexer import index_document_task
from app.utils.storage_util import upload_to_s3
import logging

logger = logging.getLogger(__name__)


class KnowledgeMediator:
    def __init__(self, knowledge_repo: KnowledgeRepository):
        self.repo = knowledge_repo

    async def ingest_document(self, tenant_id: str, file: UploadFile, file_type: str):
        # 1. Upload raw file to S3
        file_bytes = await file.read()
        file_url   = await upload_to_s3(file_bytes, file.filename, tenant_id)

        # 2. Create DB record (status=pending)
        doc = await self.repo.create(
            tenant_id=tenant_id,
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
                tenant_id = tenant_id,
                file_url  = file_url,
                file_type = file_type,
            ),
        )

        return doc

    async def delete_document(self, doc_id: str):
        doc = await self.repo.get_by_id(doc_id)
        # Remove from Qdrant (by doc_id metadata filter)
        await self.repo.delete_qdrant_chunks(doc_id, doc.tenant_id)
        # Delete DB record
        await self.repo.delete(doc_id)

    async def reindex_document(self, doc_id: str):
        doc = await self.repo.get_by_id(doc_id)
        await self.repo.update_status(doc_id, "pending")
        index_document_task.delay(
            doc_id=doc_id,
            tenant_id=str(doc.tenant_id),
            file_url=doc.file_url,
            file_type=doc.file_type,
        )
```

---

## Step 6 — AI Services

### `app/services/ai/agent_service.py`
```python
from openai import AsyncOpenAI
from app.services.ai.rag_service import RAGService
from app.services.ai.memory_service import MemoryService
from app.services.ai.prompt_builder import PromptBuilder
from app.services.ai.guardrails_service import GuardrailsService
import logging

logger = logging.getLogger(__name__)


class AgentService:
    def __init__(
        self,
        rag: RAGService,
        memory: MemoryService,
        prompt_builder: PromptBuilder,
        guardrails: GuardrailsService,
        openai: AsyncOpenAI,
    ):
        self.rag            = rag
        self.memory         = memory
        self.prompt_builder = prompt_builder
        self.guardrails     = guardrails
        self.llm            = openai

    async def process_message(
        self,
        conversation_id: str,
        tenant_config: dict,
        message: str,
    ) -> tuple[str, float]:
        """Returns (response_text, confidence_score)"""

        # 1. Load conversation history from Redis
        history = await self.memory.get_history(conversation_id)

        # 2. Retrieve relevant knowledge from Qdrant
        knowledge = await self.rag.retrieve(
            query=message,
            tenant_id=tenant_config["id"],
            top_k=5,
        )

        # 3. Build system prompt dynamically
        system_prompt = self.prompt_builder.build(
            persona_name    = tenant_config.get("persona_name", "Assistant"),
            business_name   = tenant_config.get("business_name", ""),
            tone            = tenant_config.get("tone", "friendly and professional"),
            knowledge_context = knowledge,
            hard_rules      = tenant_config.get("hard_rules", []),
        )

        # 4. LLM inference
        response = await self.llm.chat.completions.create(
            model       = tenant_config.get("model", "gpt-4o"),
            messages    = [
                {"role": "system", "content": system_prompt},
                *history,
                {"role": "user",   "content": message},
            ],
            temperature = tenant_config.get("temperature", 0.7),
            max_tokens  = tenant_config.get("max_tokens", 800),
        )

        raw_response = response.choices[0].message.content

        # 5. Run guardrails (safety + confidence check)
        safe_response, confidence = await self.guardrails.validate(
            response      = raw_response,
            tenant_config = tenant_config,
        )

        # 6. Save response to memory
        await self.memory.append(conversation_id, "assistant", safe_response)

        logger.info("AI response generated", extra={
            "conversation_id": conversation_id,
            "tokens_used": response.usage.total_tokens,
            "confidence": confidence,
        })

        return safe_response, confidence
```

---

### `app/services/ai/rag_service.py`
```python
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from openai import AsyncOpenAI


class RAGService:
    def __init__(self, qdrant: AsyncQdrantClient, openai: AsyncOpenAI, collection: str):
        self.qdrant     = qdrant
        self.openai     = openai
        self.collection = collection

    async def retrieve(self, query: str, tenant_id: str, top_k: int = 5) -> str:
        # 1. Embed the query
        embed_resp = await self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=query,
        )
        query_vector = embed_resp.data[0].embedding

        # 2. Search Qdrant — filtered by tenant_id
        results = await self.qdrant.search(
            collection_name = self.collection,
            query_vector    = query_vector,
            query_filter    = Filter(must=[
                FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))
            ]),
            limit           = top_k,
            score_threshold = 0.72,
        )

        if not results:
            return "No relevant knowledge found for this query."

        # 3. Format as numbered context
        chunks = [f"[{i+1}] {r.payload['content']}" for i, r in enumerate(results)]
        return "\n\n".join(chunks)
```

---

### `app/services/ai/memory_service.py`
```python
import json
from redis.asyncio import Redis


class MemoryService:
    def __init__(self, redis: Redis, window: int = 20):
        self.redis  = redis
        self.window = window
        self.ttl    = 7200   # 2 hours

    def _key(self, conversation_id: str) -> str:
        return f"conv:memory:{conversation_id}"

    async def get_history(self, conversation_id: str) -> list[dict]:
        raw = await self.redis.get(self._key(conversation_id))
        return json.loads(raw) if raw else []

    async def append(self, conversation_id: str, role: str, content: str) -> None:
        history = await self.get_history(conversation_id)
        history.append({"role": role, "content": content})
        # Keep only last N messages (sliding window)
        history = history[-self.window:]
        await self.redis.setex(
            self._key(conversation_id), self.ttl, json.dumps(history)
        )

    async def clear(self, conversation_id: str) -> None:
        await self.redis.delete(self._key(conversation_id))
```

---

### `app/services/ai/prompt_builder.py`
```python
class PromptBuilder:
    def build(
        self,
        persona_name: str,
        business_name: str,
        tone: str,
        knowledge_context: str,
        hard_rules: list[str],
    ) -> str:
        rules_text = "\n".join(f"- {r}" for r in hard_rules) if hard_rules else "None"

        return f"""You are {persona_name}, a sales representative at {business_name}.
Communicate in a {tone} style.

PERSONALITY RULES:
- Keep replies short and conversational (2-4 sentences max per message)
- Never say you are an AI. If directly asked, say "I am a virtual assistant"
- Ask only ONE follow-up question at a time
- Use the customer's name when you know it
- Acknowledge before answering ("Great question!" / "Absolutely!")

BUSINESS KNOWLEDGE — use ONLY this to answer pricing and service questions:
{knowledge_context}

HARD RULES — never break these:
{rules_text}
- Never quote prices not found in the knowledge above
- If you don't know the answer, say "Let me get the exact details for you"
  and stop — this triggers escalation to a human
- Never mention competitor brands
- Never share other customers' information"""
```

---

### `app/services/ai/guardrails_service.py`
```python
ESCALATION_KEYWORDS = [
    "talk to a person", "human agent", "real person",
    "speak to someone", "manager please", "connect me to staff",
]

UNCERTAINTY_PHRASES = [
    "i think", "i believe", "probably", "maybe",
    "i am not sure", "i cannot find", "i don't know",
]


class GuardrailsService:
    async def validate(
        self,
        response: str,
        tenant_config: dict,
    ) -> tuple[str, float]:
        """Returns (safe_response, confidence_score 0.0–1.0)"""

        # Confidence heuristic — uncertainty phrases lower score
        text_lower = response.lower()
        hits = sum(1 for phrase in UNCERTAINTY_PHRASES if phrase in text_lower)
        confidence = max(0.3, 1.0 - (hits * 0.2))

        # Block competitor mentions if configured
        blocked_words = tenant_config.get("blocked_words", [])
        for word in blocked_words:
            response = response.replace(word, "[REDACTED]")

        return response, confidence

    def check_escalation_trigger(self, customer_message: str) -> bool:
        """Returns True if customer is explicitly asking for a human."""
        msg_lower = customer_message.lower()
        return any(kw in msg_lower for kw in ESCALATION_KEYWORDS)
```

---

### `app/services/ai/human_behavior_service.py`
```python
import random


def calculate_typing_delay(response_text: str) -> float:
    """
    Simulates human typing speed.
    Returns delay in seconds before sending the message.
    """
    CHARS_PER_SECOND = 8    # ~96 WPM average typing speed
    MIN_DELAY        = 1.5  # Never respond instantly
    MAX_DELAY        = 6.0  # Never keep waiting too long

    base   = len(response_text) / CHARS_PER_SECOND
    jitter = random.uniform(-0.4, 1.0)
    return max(MIN_DELAY, min(MAX_DELAY, base + jitter))
```

---

### `app/services/ai/lead_scorer.py`
```python
from app.repositories.lead_repository import LeadRepository
import logging

logger = logging.getLogger(__name__)

SIGNAL_SCORES = {
    "asks_pricing":      20,
    "asks_availability": 25,
    "mentions_budget":   20,
    "asks_to_book":      30,
    "name_provided":     10,
    "just_browsing":    -15,
}

STAGE_MAP = [
    (86, "qualified"),
    (61, "hot"),
    (31, "warm"),
    (0,  "cold"),
]


class LeadScorer:
    def __init__(self, lead_repo: LeadRepository):
        self.repo = lead_repo

    async def update_from_message(
        self,
        lead_id: str,
        message: str,
    ) -> None:
        lead      = await self.repo.get_by_id(lead_id)
        msg_lower = message.lower()
        delta     = 0

        if any(w in msg_lower for w in ["price", "cost", "how much", "rate", "fee"]):
            delta += SIGNAL_SCORES["asks_pricing"]
        if any(w in msg_lower for w in ["available", "when", "date", "slot", "schedule"]):
            delta += SIGNAL_SCORES["asks_availability"]
        if any(w in msg_lower for w in ["budget", "afford", "spend", "pay"]):
            delta += SIGNAL_SCORES["mentions_budget"]
        if any(w in msg_lower for w in ["book", "reserve", "appointment", "buy", "purchase"]):
            delta += SIGNAL_SCORES["asks_to_book"]
        if any(w in msg_lower for w in ["just looking", "not now", "maybe later", "no thanks"]):
            delta += SIGNAL_SCORES["just_browsing"]

        new_score = max(0, min(100, lead.score + delta))
        new_stage = next(stage for threshold, stage in STAGE_MAP if new_score >= threshold)

        await self.repo.update_score(lead_id, score=new_score, stage=new_stage)

        # Notify human agent when lead becomes qualified
        if new_stage == "qualified" and lead.stage != "qualified":
            logger.info(f"Lead {lead_id} became QUALIFIED — alert agent")
            # TODO: trigger notification_service in Phase 2
```

---

### `app/services/channels/base_channel.py`
```python
from abc import ABC, abstractmethod


class BaseChannel(ABC):
    @abstractmethod
    async def send_message(self, recipient: str, message: str, **kwargs) -> dict:
        """Send a text message to the recipient."""
        ...

    @abstractmethod
    async def download_media(self, media_id: str, **kwargs) -> bytes:
        """Download media (audio/image) by media ID."""
        ...
```

---

### `app/services/channels/whatsapp_channel.py`
```python
import httpx
from app.services.channels.base_channel import BaseChannel


class WhatsAppChannel(BaseChannel):
    def __init__(self, api_version: str, app_secret: str):
        self.api_version = api_version
        self.base_url    = f"https://graph.facebook.com/{api_version}"
        self.app_secret  = app_secret

    async def send_message(
        self,
        recipient: str,
        message: str,
        phone_number_id: str = None,
        access_token: str = None,
        **kwargs,
    ) -> dict:
        url     = f"{self.base_url}/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type":  "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to":   recipient,
            "type": "text",
            "text": {"body": message},
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def download_media(self, media_id: str, access_token: str = None, **kwargs) -> bytes:
        """Download audio/image from Meta servers."""
        # Step 1: Get media URL
        url_resp = await httpx.AsyncClient().get(
            f"{self.base_url}/{media_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        media_url = url_resp.json()["url"]

        # Step 2: Download actual file
        file_resp = await httpx.AsyncClient().get(
            media_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return file_resp.content
```

---

## Step 7 — Repositories

### `app/repositories/tenant_repository.py`
```python
from app.repositories.base_repository import BaseRepository
from app.models.tenant_model import Tenant
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class TenantRepository(BaseRepository[Tenant]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Tenant)

    async def get_by_slug(self, slug: str) -> Tenant | None:
        result = await self.db.execute(select(Tenant).where(Tenant.slug == slug))
        return result.scalar_one_or_none()

    async def update_usage(self, tenant_id: str, messages: int = 1, tokens: int = 0):
        tenant = await self.get_by_id(tenant_id)
        if tenant:
            tenant.monthly_message_count += messages
            tenant.monthly_token_count   += tokens
            await self.db.commit()
```

---

### `app/repositories/conversation_repository.py`
```python
from app.repositories.base_repository import BaseRepository
from app.models.conversation_model import Conversation
from app.models.message_model import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import uuid


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Conversation)

    async def get_or_create(
        self,
        tenant_id: str,
        customer_phone: str,
        channel: str,
        customer_name: str | None = None,
    ) -> Conversation:
        # Check if an active conversation already exists
        result = await self.db.execute(
            select(Conversation).where(
                Conversation.tenant_id      == uuid.UUID(tenant_id),
                Conversation.customer_phone == customer_phone,
                Conversation.channel        == channel,
                Conversation.status         == "active",
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        # Create new conversation
        conversation = Conversation(
            tenant_id      = uuid.UUID(tenant_id),
            customer_phone = customer_phone,
            channel        = channel,
            customer_name  = customer_name,
        )
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        return conversation

    async def add_message(
        self,
        conversation_id: str,
        tenant_id: str,
        role: str,
        content: str,
        media_type: str | None = None,
        tokens_used: int | None = None,
        latency_ms: int | None = None,
    ) -> Message:
        message = Message(
            conversation_id = uuid.UUID(conversation_id),
            tenant_id       = uuid.UUID(tenant_id),
            role            = role,
            content         = content,
            media_type      = media_type,
            tokens_used     = tokens_used,
            latency_ms      = latency_ms,
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_with_messages(self, conversation_id: str) -> Conversation | None:
        result = await self.db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == uuid.UUID(conversation_id))
        )
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self,
        tenant_id: str,
        status: str | None = None,
        channel: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        query = select(Conversation).where(Conversation.tenant_id == uuid.UUID(tenant_id))
        if status:
            query = query.where(Conversation.status == status)
        if channel:
            query = query.where(Conversation.channel == channel)
        query  = query.order_by(Conversation.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_status(
        self,
        conversation_id: str,
        status: str,
        agent_id: str | None = None,
    ) -> None:
        conv = await self.get_by_id(conversation_id)
        if conv:
            conv.status           = status
            conv.assigned_agent_id = uuid.UUID(agent_id) if agent_id else None
            await self.db.commit()
```

---

### `app/repositories/lead_repository.py`
```python
from app.repositories.base_repository import BaseRepository
from app.models.lead_model import Lead
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid


class LeadRepository(BaseRepository[Lead]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Lead)

    async def get_or_create(
        self,
        tenant_id: str,
        conversation_id: str,
        customer_phone: str,
    ) -> Lead:
        result = await self.db.execute(
            select(Lead).where(Lead.conversation_id == uuid.UUID(conversation_id))
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        lead = Lead(
            tenant_id       = uuid.UUID(tenant_id),
            conversation_id = uuid.UUID(conversation_id),
            customer_phone  = customer_phone,
        )
        self.db.add(lead)
        await self.db.commit()
        await self.db.refresh(lead)
        return lead

    async def update_score(self, lead_id: str, score: int, stage: str) -> None:
        lead = await self.get_by_id(lead_id)
        if lead:
            lead.score = score
            lead.stage = stage
            await self.db.commit()

    async def list_by_tenant(
        self,
        tenant_id: str,
        stage: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Lead]:
        query = select(Lead).where(Lead.tenant_id == uuid.UUID(tenant_id))
        if stage:
            query = query.where(Lead.stage == stage)
        query  = query.order_by(Lead.score.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return result.scalars().all()
```

---

### `app/repositories/knowledge_repository.py`
```python
from app.repositories.base_repository import BaseRepository
from app.models.knowledge_doc_model import KnowledgeDoc
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
import uuid


class KnowledgeRepository(BaseRepository[KnowledgeDoc]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, KnowledgeDoc)

    async def create(self, tenant_id: str, filename: str, file_type: str, file_url: str) -> KnowledgeDoc:
        doc = KnowledgeDoc(
            tenant_id = uuid.UUID(tenant_id),
            filename  = filename,
            file_type = file_type,
            file_url  = file_url,
            status    = "pending",
        )
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def update_status(self, doc_id: str, status: str, chunk_count: int = 0) -> None:
        doc = await self.get_by_id(doc_id)
        if doc:
            doc.status      = status
            doc.chunk_count = chunk_count
            await self.db.commit()

    async def list_by_tenant(self, tenant_id: str) -> list[KnowledgeDoc]:
        result = await self.db.execute(
            select(KnowledgeDoc)
            .where(KnowledgeDoc.tenant_id == uuid.UUID(tenant_id))
            .order_by(KnowledgeDoc.created_at.desc())
        )
        return result.scalars().all()

    async def delete_qdrant_chunks(self, doc_id: str, tenant_id: str) -> None:
        # Delete from PostgreSQL chunks table
        from app.models.knowledge_doc_model import KnowledgeChunk
        await self.db.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.doc_id == uuid.UUID(doc_id))
        )
        await self.db.commit()
        # Note: Qdrant deletion is handled in knowledge_indexer worker
```

---

## Step 8 — RabbitMQ Workers

> You already have `RabbitMQClient` in `messaging_config.py`.  
> We use it directly — no Celery needed. Two consumers run as long-lived async tasks:  
> **`ai_message_consumer`** (processes customer messages) and **`knowledge_consumer`** (indexes documents).

---

### How it works

```
message_mediator.publish()
      |
      v
RabbitMQ exchange: "ai"
  ├── routing_key: "ai.messages"  →  ai_message_consumer  →  AI pipeline → WhatsApp
  └── routing_key: "ai.knowledge" →  knowledge_consumer   →  embed + Qdrant
```

---

### `app/workers/__init__.py`
```python
# empty — marks workers as a package
```

---

### `app/workers/ai_message_consumer.py`
```python
"""
Long-lived RabbitMQ consumer for AI message processing.
Started inside FastAPI lifespan via asyncio.create_task().
"""
import asyncio
import logging
from app.configs.messaging_config import RabbitMQClient
from app.configs.app_config import get_settings
from app.services.ai.agent_service import AgentService
from app.services.ai.rag_service import RAGService
from app.services.ai.memory_service import MemoryService
from app.services.ai.prompt_builder import PromptBuilder
from app.services.ai.guardrails_service import GuardrailsService
from app.services.ai.lead_scorer import LeadScorer
from app.services.ai.human_behavior_service import calculate_typing_delay
from app.services.channels.whatsapp_channel import WhatsAppChannel
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.tenant_repository import TenantRepository
from app.repositories.lead_repository import LeadRepository

logger   = logging.getLogger(__name__)
settings = get_settings()


async def start_ai_message_consumer(rabbitmq: RabbitMQClient) -> None:
    """
    Bind to exchange="ai", routing_key="ai.messages".
    Called once in main.py lifespan startup.
    """
    await rabbitmq.consume(
        exchange     = "ai",
        queue_name   = "ai.messages.queue",
        routing_keys = ["ai.messages"],
        callback     = handle_message,
    )
    logger.info("AI message consumer started — listening on ai.messages.queue")


async def handle_message(payload: dict) -> None:
    """
    Called by RabbitMQClient for every message on ai.messages.queue.
    payload keys: conversation_id, lead_id, tenant_id,
                  message_text, media_type, media_id, channel
    """
    conversation_id = payload["conversation_id"]
    lead_id         = payload["lead_id"]
    tenant_id       = payload["tenant_id"]
    message_text    = payload["message_text"]
    media_type      = payload.get("media_type")
    media_id        = payload.get("media_id")
    channel         = payload["channel"]

    try:
        await _process(
            conversation_id, lead_id, tenant_id,
            message_text, media_type, media_id, channel,
        )
    except Exception as exc:
        logger.error(f"AI message processing failed: {exc}", exc_info=True)
        raise   # RabbitMQ will re-queue (message.process() context manager)


async def _process(
    conversation_id: str,
    lead_id: str,
    tenant_id: str,
    message_text: str,
    media_type: str | None,
    media_id: str | None,
    channel: str,
) -> None:

    # --- Repositories ---
    tenant_repo = TenantRepository()
    conv_repo   = ConversationRepository()
    lead_repo   = LeadRepository()

    tenant         = await tenant_repo.get_by_id(tenant_id)
    channel_client = WhatsAppChannel(
        api_version = settings.WHATSAPP_API_VERSION,
        app_secret  = settings.META_APP_SECRET,
    )

    # --- Handle voice or image if media present ---
    if media_type == "audio" and media_id:
        audio_bytes  = await channel_client.download_media(media_id, access_token=tenant.whatsapp_access_token)
        message_text = await _transcribe_voice(audio_bytes)

    elif media_type == "image" and media_id:
        image_bytes  = await channel_client.download_media(media_id, access_token=tenant.whatsapp_access_token)
        message_text = await _describe_image(image_bytes, message_text)

    # --- Check explicit escalation request ---
    guardrails = GuardrailsService()
    if guardrails.check_escalation_trigger(message_text):
        await _escalate(conversation_id, conv_repo)
        return

    # --- AI pipeline ---
    from openai import AsyncOpenAI
    from qdrant_client import AsyncQdrantClient

    agent = AgentService(
        rag            = RAGService(
                             qdrant     = AsyncQdrantClient(url=settings.QDRANT_URL),
                             openai     = AsyncOpenAI(api_key=settings.OPENAI_API_KEY),
                             collection = settings.QDRANT_COLLECTION,
                         ),
        memory         = MemoryService(redis=..., window=settings.AI_MEMORY_WINDOW),
        prompt_builder = PromptBuilder(),
        guardrails     = guardrails,
        openai         = AsyncOpenAI(api_key=settings.OPENAI_API_KEY),
    )

    ai_config       = tenant.ai_config or {}
    ai_config["id"] = str(tenant.id)

    response_text, confidence = await agent.process_message(
        conversation_id = conversation_id,
        tenant_config   = ai_config,
        message         = message_text,
    )

    # --- Low confidence → escalate ---
    threshold = ai_config.get("confidence_threshold", settings.AI_CONFIDENCE_THRESHOLD)
    if confidence < threshold:
        await _escalate(conversation_id, conv_repo)
        return

    # --- Update lead score ---
    scorer = LeadScorer(lead_repo)
    await scorer.update_from_message(lead_id, message_text)

    # --- Human-like delay ---
    await asyncio.sleep(calculate_typing_delay(response_text))

    # --- Send via channel ---
    await channel_client.send_message(
        recipient       = tenant.customer_phone,
        message         = response_text,
        phone_number_id = tenant.whatsapp_phone_id,
        access_token    = tenant.whatsapp_access_token,
    )

    # --- Persist AI response ---
    await conv_repo.add_message(
        conversation_id = conversation_id,
        tenant_id       = tenant_id,
        role            = "assistant",
        content         = response_text,
    )

    await tenant_repo.update_usage(tenant_id, messages=1)
    logger.info(f"AI response sent for conversation {conversation_id}")


async def _escalate(conversation_id: str, conv_repo: ConversationRepository) -> None:
    await conv_repo.update_status(conversation_id, "escalated")
    logger.info(f"Conversation {conversation_id} escalated to human")


async def _transcribe_voice(audio_bytes: bytes) -> str:
    from openai import AsyncOpenAI
    import io
    transcript = await AsyncOpenAI().audio.transcriptions.create(
        model = "whisper-1",
        file  = ("voice.ogg", io.BytesIO(audio_bytes), "audio/ogg"),
    )
    return transcript.text


async def _describe_image(image_bytes: bytes, customer_text: str) -> str:
    import base64
    from openai import AsyncOpenAI
    b64  = base64.b64encode(image_bytes).decode()
    resp = await AsyncOpenAI().chat.completions.create(
        model    = "gpt-4o",
        messages = [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            {"type": "text",      "text": customer_text or "What is in this image?"},
        ]}],
        max_tokens = 500,
    )
    return resp.choices[0].message.content
```

---

### `app/workers/knowledge_consumer.py`
```python
"""
Long-lived RabbitMQ consumer for document indexing.
Started inside FastAPI lifespan via asyncio.create_task().
"""
import asyncio
import logging
import uuid
import httpx
import io
from app.configs.messaging_config import RabbitMQClient
from app.repositories.knowledge_repository import KnowledgeRepository
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct
from openai import AsyncOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


async def start_knowledge_consumer(rabbitmq: RabbitMQClient) -> None:
    """
    Bind to exchange="ai", routing_key="ai.knowledge".
    Called once in main.py lifespan startup.
    """
    await rabbitmq.consume(
        exchange     = "ai",
        queue_name   = "ai.knowledge.queue",
        routing_keys = ["ai.knowledge"],
        callback     = handle_index_request,
    )
    logger.info("Knowledge consumer started — listening on ai.knowledge.queue")


async def handle_index_request(payload: dict) -> None:
    """
    Called by RabbitMQClient for every message on ai.knowledge.queue.
    payload keys: doc_id, tenant_id, file_url, file_type
    """
    try:
        await _index(
            doc_id    = payload["doc_id"],
            tenant_id = payload["tenant_id"],
            file_url  = payload["file_url"],
            file_type = payload["file_type"],
        )
    except Exception as exc:
        logger.error(f"Knowledge indexing failed: {exc}", exc_info=True)
        raise


async def _index(doc_id: str, tenant_id: str, file_url: str, file_type: str) -> None:
    repo = KnowledgeRepository()

    try:
        await repo.update_status(doc_id, "processing")

        # 1. Download file
        async with httpx.AsyncClient() as client:
            resp    = await client.get(file_url)
            content = resp.content

        # 2. Extract text based on file type
        text = _extract_text(content, file_type)

        # 3. Chunk with overlap
        splitter = RecursiveCharacterTextSplitter(
            chunk_size    = 500,
            chunk_overlap = 50,
            separators    = ["

", "
", ". ", " "],
        )
        chunks = splitter.split_text(text)

        # 4. Embed all chunks in single API call
        openai     = AsyncOpenAI()
        embed_resp = await openai.embeddings.create(
            model = "text-embedding-3-small",
            input = chunks,
        )
        vectors = [e.embedding for e in embed_resp.data]

        # 5. Upsert into Qdrant filtered by tenant_id
        qdrant = AsyncQdrantClient()
        points = [
            PointStruct(
                id      = str(uuid.uuid4()),
                vector  = vec,
                payload = {
                    "tenant_id": tenant_id,
                    "doc_id":    doc_id,
                    "content":   chunk,
                },
            )
            for chunk, vec in zip(chunks, vectors)
        ]
        await qdrant.upsert(collection_name="knowledge_base", points=points)

        # 6. Mark as indexed in PostgreSQL
        await repo.update_status(doc_id, "indexed", chunk_count=len(chunks))
        logger.info(f"Indexed {len(chunks)} chunks for doc {doc_id}")

    except Exception as exc:
        await repo.update_status(doc_id, "failed")
        logger.error(f"Indexing failed for doc {doc_id}: {exc}")
        raise


def _extract_text(content: bytes, file_type: str) -> str:
    if file_type == "pdf":
        import pypdf2
        reader = pypdf2.PdfReader(io.BytesIO(content))
        return "
".join(page.extract_text() for page in reader.pages)
    elif file_type == "docx":
        from docx import Document
        doc = Document(io.BytesIO(content))
        return "
".join(para.text for para in doc.paragraphs)
    else:
        return content.decode("utf-8", errors="ignore")
```

---

### Update `message_mediator.py` — inject RabbitMQClient
```python
# app/mediator/message_mediator.py  — update __init__ and handle_inbound

from app.configs.messaging_config import RabbitMQClient   # ADD

class MessageMediator:
    def __init__(
        self,
        conversation_repo: ConversationRepository,
        tenant_repo: TenantRepository,
        lead_repo: LeadRepository,
        rabbitmq: RabbitMQClient,                         # ADD
    ):
        self.conv_repo   = conversation_repo
        self.tenant_repo = tenant_repo
        self.lead_repo   = lead_repo
        self.rabbitmq    = rabbitmq                       # ADD

    async def handle_inbound(self, tenant_id, message, channel):
        # ... (steps 1-4 unchanged) ...

        # Step 5 — publish to RabbitMQ (was: Celery .delay())
        await self.rabbitmq.publish(
            exchange    = "ai",
            routing_key = "ai.messages",
            message     = dict(
                conversation_id = str(conversation.id),
                lead_id         = str(lead.id),
                tenant_id       = tenant_id,
                message_text    = message.text or "",
                media_type      = message.media_type,
                media_id        = message.media_id,
                channel         = channel,
            ),
        )
```

---

### Update `knowledge_mediator.py` — inject RabbitMQClient
```python
# app/mediator/knowledge_mediator.py  — update __init__ and ingest_document

from app.configs.messaging_config import RabbitMQClient   # ADD

class KnowledgeMediator:
    def __init__(
        self,
        knowledge_repo: KnowledgeRepository,
        rabbitmq: RabbitMQClient,                         # ADD
    ):
        self.repo     = knowledge_repo
        self.rabbitmq = rabbitmq                          # ADD

    async def ingest_document(self, tenant_id, file, file_type):
        # ... (steps 1-2 unchanged) ...

        # Step 3 — publish to RabbitMQ (was: Celery .delay())
        await self.rabbitmq.publish(
            exchange    = "ai",
            routing_key = "ai.knowledge",
            message     = dict(
                doc_id    = str(doc.id),
                tenant_id = tenant_id,
                file_url  = file_url,
                file_type = file_type,
            ),
        )
        return doc
```

---

## Step 9 — Security Util Extension

### `app/utils/security_util.py` (add to existing file)
```python
import hmac
import hashlib
from fastapi import HTTPException
from app.configs.app_config import get_settings


def verify_whatsapp_signature(body: bytes, signature_header: str) -> None:
    """Verify Meta HMAC-SHA256 webhook signature. Raises 403 if invalid."""
    settings = get_settings()

    if not signature_header.startswith("sha256="):
        raise HTTPException(403, "Missing or invalid webhook signature")

    expected = hmac.new(
        settings.META_APP_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    received = signature_header.split("sha256=", 1)[1]

    if not hmac.compare_digest(expected, received):
        raise HTTPException(403, "Webhook signature mismatch")
```

---

## Step 10 — DI Container Extension

### `app/di/container.py` (extend existing)
```python
# Add these imports and providers to your existing Container class

from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient
from app.configs.messaging_config import RabbitMQClient
from app.services.ai.agent_service import AgentService
from app.services.ai.rag_service import RAGService
from app.services.ai.memory_service import MemoryService
from app.services.ai.prompt_builder import PromptBuilder
from app.services.ai.guardrails_service import GuardrailsService
from app.services.channels.whatsapp_channel import WhatsAppChannel
from app.repositories.tenant_repository import TenantRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.knowledge_repository import KnowledgeRepository
from app.mediator.message_mediator import MessageMediator
from app.mediator.knowledge_mediator import KnowledgeMediator
from app.edge.http.controller.webhook_controller import WebhookController
from app.edge.http.controller.conversation_controller import ConversationController
from app.edge.http.controller.knowledge_controller import KnowledgeController
from app.edge.http.controller.lead_controller import LeadController


# --- Inside your Container class ---

# RabbitMQ (your existing messaging_config.py)
rabbitmq = providers.Singleton(
    RabbitMQClient,
    host         = config.RABBITMQ_HOST,
    port         = config.RABBITMQ_PORT,
    username     = config.RABBITMQ_USERNAME,
    password     = config.RABBITMQ_PASSWORD,
    virtual_host = config.RABBITMQ_VIRTUAL_HOST,
)

# AI clients
openai_client = providers.Singleton(AsyncOpenAI, api_key=config.OPENAI_API_KEY)
qdrant_client = providers.Singleton(AsyncQdrantClient, url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY)

# AI services
rag_service     = providers.Factory(RAGService, qdrant=qdrant_client, openai=openai_client, collection=config.QDRANT_COLLECTION)
memory_service  = providers.Factory(MemoryService, redis=redis, window=config.AI_MEMORY_WINDOW)
prompt_builder  = providers.Singleton(PromptBuilder)
guardrails      = providers.Singleton(GuardrailsService)
agent_service   = providers.Factory(AgentService, rag=rag_service, memory=memory_service,
                                     prompt_builder=prompt_builder, guardrails=guardrails, openai=openai_client)

# Channel clients
whatsapp_channel = providers.Factory(WhatsAppChannel, api_version=config.WHATSAPP_API_VERSION,
                                      app_secret=config.META_APP_SECRET)

# Repositories
tenant_repo       = providers.Factory(TenantRepository, db=db_session)
conversation_repo = providers.Factory(ConversationRepository, db=db_session)
lead_repo         = providers.Factory(LeadRepository, db=db_session)
knowledge_repo    = providers.Factory(KnowledgeRepository, db=db_session)

# Mediators
message_mediator  = providers.Factory(MessageMediator, conversation_repo=conversation_repo,
                                       tenant_repo=tenant_repo, lead_repo=lead_repo,
                                       rabbitmq=rabbitmq)
knowledge_mediator = providers.Factory(KnowledgeMediator, knowledge_repo=knowledge_repo,
                                        rabbitmq=rabbitmq)

# Controllers
webhook_controller      = providers.Factory(WebhookController, message_mediator=message_mediator,
                                             tenant_repo=tenant_repo)
conversation_controller = providers.Factory(ConversationController, conversation_repo=conversation_repo)
knowledge_controller    = providers.Factory(KnowledgeController, knowledge_repo=knowledge_repo,
                                             knowledge_mediator=knowledge_mediator)
lead_controller         = providers.Factory(LeadController, lead_repo=lead_repo)
```

---

## Step 11 — Register Routes in main.py

### `app/main.py` (extend existing)
```python
from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from app.di.container import Container
from app.edge.http.routes import (
    webhook_route,
    conversation_route,
    knowledge_route,
    lead_route,
)
from app.workers.ai_message_consumer import start_ai_message_consumer
from app.workers.knowledge_consumer import start_knowledge_consumer
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams
from app.configs.app_config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Your existing startup code ---

    # --- New 1: Initialize Qdrant collection ---
    qdrant      = AsyncQdrantClient(url=settings.QDRANT_URL)
    collections = await qdrant.get_collections()
    names       = [c.name for c in collections.collections]
    if settings.QDRANT_COLLECTION not in names:
        await qdrant.create_collection(
            collection_name = settings.QDRANT_COLLECTION,
            vectors_config  = VectorParams(size=1536, distance=Distance.COSINE),
        )

    # --- New 2: Connect RabbitMQ and start consumers ---
    container = Container()
    rabbitmq  = container.rabbitmq()
    await rabbitmq.connect()

    # Start both consumers as background tasks (non-blocking)
    asyncio.create_task(start_ai_message_consumer(rabbitmq))
    asyncio.create_task(start_knowledge_consumer(rabbitmq))

    yield

    # --- Shutdown: disconnect RabbitMQ ---
    await rabbitmq.disconnect()
    # --- Your existing shutdown code ---


app = FastAPI(lifespan=lifespan)

# --- Your existing routers (unchanged) ---
app.include_router(auth_route.router,  prefix="/api/v1")
app.include_router(users_route.router, prefix="/api/v1")
app.include_router(health_route.router)

# --- New AI Sales Agent routers ---
app.include_router(webhook_route.router,      prefix="/api/v1")
app.include_router(conversation_route.router, prefix="/api/v1")
app.include_router(knowledge_route.router,    prefix="/api/v1")
app.include_router(lead_route.router,         prefix="/api/v1")
```

---

## Step 12 — Docker Compose Extension

> RabbitMQ is already in your `docker-compose.yml` via `messaging_config.py`.  
> Only add **Qdrant** — no new worker containers needed.  
> Consumers start automatically inside the FastAPI process via `lifespan`.

### `docker-compose.yml` (append to existing services)
```yaml
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped

volumes:
  qdrant_data:
```

> That's it. No celery-worker, no celery-beat, no flower.  
> Workers live inside the FastAPI app — started in `main.py` lifespan.

---

## Step 13 — New .env Variables

```bash
# Add to your existing .env

# AI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
AI_TEMPERATURE=0.7
AI_MAX_TOKENS=800
AI_MEMORY_WINDOW=20
AI_CONFIDENCE_THRESHOLD=0.75

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=knowledge_base

# RabbitMQ (already in your .env — just confirm these exist)
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USERNAME=admin
RABBITMQ_PASSWORD=admin
RABBITMQ_VIRTUAL_HOST=/

# Meta / WhatsApp
META_APP_SECRET=your-meta-app-secret
WHATSAPP_API_VERSION=v21.0
```

---

## Step 14 — New pip Dependencies

```txt
# Add to requirements.txt
openai>=1.51.0
qdrant-client>=1.11.0
langchain>=0.3.0
langchain-openai>=0.2.0
langchain-community>=0.3.0
aio_pika>=9.4.0        # RabbitMQ async client (already in your project)
# No Celery needed — workers run inside FastAPI via lifespan
pypdf2>=3.0.0
python-docx>=1.1.0
tiktoken>=0.7.0
langdetect>=1.0.9
cryptography>=43.0.0
```

---

## Phase 1 Build Order Checklist

```
Week 1
  [ ] Step 1  — Create all 5 models + run alembic migrations
  [ ] Step 2  — Create all schemas
  [ ] Step 13 — Add env vars to .env
  [ ] Step 14 — pip install new dependencies

Week 2
  [ ] Step 3  — Create all routes
  [ ] Step 4  — Create all controllers
  [ ] Step 5  — Create both mediators

Week 3
  [ ] Step 6  — Create all AI services (agent, rag, memory, prompt_builder, guardrails, lead_scorer, human_behavior)
  [ ] Step 6  — Create channel services (base + whatsapp)
  [ ] Step 7  — Create all repositories

Week 4
  [ ] Step 8  — Create RabbitMQ workers (ai_message_consumer + knowledge_consumer)
  [ ] Step 9  — Extend security_util.py
  [ ] Step 10 — Extend DI container
  [ ] Step 11 — Register routes in main.py
  [ ] Step 12 — Extend docker-compose.yml
  [ ] Test end-to-end: POST webhook → RabbitMQ → AI consumer → WhatsApp response
```

---

# PHASE 2 — Multi-Channel (Months 4–7)

> Add Instagram, Facebook, WebSocket chat, voice/image support, CRM integration, analytics.

---

## Step 1 — New Schemas

### `app/schemas/channel_schema.py`
```python
from pydantic import BaseModel as PydanticBase
from typing import Optional


class ChannelConfigCreate(PydanticBase):
    channel_type: str       # instagram | facebook | web
    credentials: dict       # encrypted before storage


# Instagram webhook payload
class InstagramMessage(PydanticBase):
    sender_id: str
    recipient_id: str
    text: Optional[str] = None
    attachments: Optional[list] = None
```

---

## Step 2 — New Routes

### `app/edge/http/routes/analytics_route.py`
```python
from fastapi import APIRouter, Query
from app.di.container import Container
from dependency_injector.wiring import inject, Provide

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary")
@inject
async def get_summary(
    tenant_id: str,
    days: int = Query(30),
    controller=Provide[Container.analytics_controller],
):
    return await controller.get_summary(tenant_id, days)


@router.get("/leads/funnel")
@inject
async def lead_funnel(
    tenant_id: str,
    controller=Provide[Container.analytics_controller],
):
    return await controller.get_lead_funnel(tenant_id)
```

---

## Step 3 — New Routes (webhook extension)

### `app/edge/http/routes/webhook_route.py` (add to existing)
```python
@router.post("/instagram/{tenant_id}")
@inject
async def receive_instagram(
    tenant_id: str, request: Request, background_tasks: BackgroundTasks,
    controller=Provide[Container.webhook_controller],
):
    return await controller.handle_instagram(tenant_id, request, background_tasks)

@router.post("/facebook/{tenant_id}")
@inject
async def receive_facebook(
    tenant_id: str, request: Request, background_tasks: BackgroundTasks,
    controller=Provide[Container.webhook_controller],
):
    return await controller.handle_facebook(tenant_id, request, background_tasks)
```

---

## Step 4 — WebSocket Route

### `app/edge/socket/socket_route.py` (extend existing)
```python
from fastapi import WebSocket, WebSocketDisconnect
from app.edge.socket.connection_manager import ConnectionManager
from app.services.ai.agent_service import AgentService
from app.services.ai.human_behavior_service import calculate_typing_delay
from uuid import uuid4
import asyncio

manager = ConnectionManager()


@router.websocket("/ws/chat/{tenant_slug}")
async def websocket_chat(websocket: WebSocket, tenant_slug: str):
    session_id = str(uuid4())
    await manager.connect(websocket, session_id)

    try:
        while True:
            data     = await websocket.receive_json()
            msg_text = data.get("message", "")

            # Show typing indicator
            await websocket.send_json({"type": "typing", "active": True})

            # Get tenant config by slug
            tenant_config = await get_tenant_config_by_slug(tenant_slug)

            # Run AI inline (no RabbitMQ for WebSocket — needs real-time response)
            agent = AgentService(...)
            response, _ = await agent.process_message(
                conversation_id = session_id,
                tenant_config   = tenant_config,
                message         = msg_text,
            )

            await asyncio.sleep(calculate_typing_delay(response))
            await websocket.send_json({"type": "typing", "active": False})
            await websocket.send_json({"type": "message", "content": response})

    except WebSocketDisconnect:
        manager.disconnect(session_id)
```

---

## Step 5 — New Channel Services

### `app/services/channels/instagram_channel.py`
```python
import httpx
from app.services.channels.base_channel import BaseChannel


class InstagramChannel(BaseChannel):
    BASE_URL = "https://graph.facebook.com/v21.0"

    async def send_message(self, recipient: str, message: str, access_token: str = None, **kwargs):
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.BASE_URL}/me/messages",
                json   = {"recipient": {"id": recipient}, "message": {"text": message}},
                params = {"access_token": access_token},
            )

    async def download_media(self, media_id: str, **kwargs) -> bytes:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/{media_id}/")
            return resp.content
```

---

## Step 6 — CRM Integration Services

### `app/services/integrations/hubspot_service.py`
```python
import httpx


class HubSpotService:
    BASE_URL = "https://api.hubapi.com"

    def __init__(self, api_key: str):
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async def create_contact(self, phone: str, name: str, email: str = None) -> dict:
        payload = {"properties": {"phone": phone, "firstname": name, "email": email or ""}}
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.BASE_URL}/crm/v3/objects/contacts",
                                     json=payload, headers=self.headers)
            return resp.json()

    async def create_deal(self, contact_id: str, deal_name: str, stage: str = "appointmentscheduled") -> dict:
        payload = {"properties": {"dealname": deal_name, "dealstage": stage},
                   "associations": [{"to": {"id": contact_id}, "types": [{"category": "HUBSPOT_DEFINED", "typeId": 3}]}]}
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.BASE_URL}/crm/v3/objects/deals",
                                     json=payload, headers=self.headers)
            return resp.json()
```

---

# PHASE 3 — Enterprise SaaS (Months 8–14)

> Microservices split, Kafka event bus, Kubernetes, Stripe billing, PostgreSQL RLS.

---

## Step 1 — PostgreSQL Row-Level Security

```sql
-- Run once per tenant-scoped table after Phase 3 migration

ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages      ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads         ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_docs ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_conversations ON conversations
  USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_messages ON messages
  USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_leads ON leads
  USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

```python
# app/core/db_middleware.py — set tenant context before every query
async def set_tenant_context(db: AsyncSession, tenant_id: str):
    await db.execute(
        text("SELECT set_config('app.current_tenant', :tid, true)"),
        {"tid": tenant_id},
    )
```

---

## Step 2 — Prometheus Metrics

### `app/configs/monitoring_config.py` (extend existing)
```python
from prometheus_client import Counter, Histogram, Gauge

# Add alongside your existing metrics:
ai_messages_processed = Counter(
    "ai_messages_processed_total",
    "Messages processed by AI",
    ["tenant_id", "channel", "status"],
)
ai_response_latency = Histogram(
    "ai_response_latency_seconds",
    "AI pipeline latency",
    ["model"],
    buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 10.0],
)
ai_token_cost = Counter(
    "ai_token_cost_total",
    "Total tokens consumed",
    ["tenant_id", "model"],
)
ai_escalation_rate = Counter(
    "ai_escalations_total",
    "Conversations escalated to human",
    ["tenant_id", "reason"],
)
```

---

## Step 3 — Kafka Topics (replace BackgroundTasks for inter-service comms)

```python
# Topic names — publish/consume these between microservices
TOPICS = {
    "messages_inbound":         "ai.messages.inbound",
    "messages_outbound":        "ai.messages.outbound",
    "leads_scored":             "ai.leads.scored",
    "leads_qualified":          "ai.leads.qualified",
    "conversations_escalated":  "ai.conversations.escalated",
    "knowledge_index_request":  "ai.knowledge.index_request",
    "billing_usage":            "ai.billing.usage",
}
```

---

# PHASE 4 — AI Business OS (Months 15–24)

> Multi-agent, QuickBooks, OCR, n8n workflow automation.

---

## Step 1 — Multi-Agent with LangGraph

### `app/services/ai/multi_agent_service.py`
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict


class AgentState(TypedDict):
    conversation_id: str
    tenant_config: dict
    customer_message: str
    selected_agent: str
    response: str


def supervisor_node(state: AgentState) -> AgentState:
    """Decide which specialist agent handles this message."""
    msg = state["customer_message"].lower()

    if any(w in msg for w in ["invoice", "payment", "paid", "receipt"]):
        state["selected_agent"] = "finance"
    elif any(w in msg for w in ["book", "appointment", "schedule", "available"]):
        state["selected_agent"] = "booking"
    elif any(w in msg for w in ["complaint", "refund", "problem", "issue"]):
        state["selected_agent"] = "support"
    else:
        state["selected_agent"] = "sales"

    return state


def route_to_agent(state: AgentState) -> str:
    return state["selected_agent"]


# Build workflow
workflow = StateGraph(AgentState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("sales",      sales_agent_node)
workflow.add_node("support",    support_agent_node)
workflow.add_node("booking",    booking_agent_node)
workflow.add_node("finance",    finance_agent_node)

workflow.set_entry_point("supervisor")
workflow.add_conditional_edges("supervisor", route_to_agent, {
    "sales":   "sales",
    "support": "support",
    "booking": "booking",
    "finance": "finance",
})
workflow.add_edge("sales",   END)
workflow.add_edge("support", END)
workflow.add_edge("booking", END)
workflow.add_edge("finance", END)

multi_agent = workflow.compile()
```

---

## Step 2 — QuickBooks Integration

### `app/services/integrations/quickbooks_service.py`
```python
import httpx


class QuickBooksService:
    def __init__(self, access_token: str, realm_id: str):
        self.token    = access_token
        self.realm_id = realm_id
        self.base_url = f"https://quickbooks.api.intuit.com/v3/company/{realm_id}"
        self.headers  = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

    async def check_payment_status(self, customer_name: str) -> dict:
        query = f"SELECT * FROM Invoice WHERE CustomerRef.name = '{customer_name}'"
        async with httpx.AsyncClient() as client:
            resp     = await client.get(f"{self.base_url}/query", params={"query": query}, headers=self.headers)
            invoices = resp.json().get("QueryResponse", {}).get("Invoice", [])

        for inv in invoices:
            if inv.get("Balance", 1) == 0:
                return {"status": "paid", "invoice_id": inv["Id"]}

        return {"status": "outstanding", "count": len(invoices)}

    async def get_invoice(self, invoice_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/invoice/{invoice_id}", headers=self.headers)
            return resp.json()
```

---

*End of implementation plan — follow steps in order within each phase.*