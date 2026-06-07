# AI Conversational Sales Agent Platform
## Complete Implementation Plan — FastAPI Boilerplate Edition

> **Stack:** FastAPI · PostgreSQL · Redis · Qdrant · Celery · OpenAI GPT-4o · WhatsApp Business API  
> **Architecture:** Clean/Hexagonal (your existing boilerplate pattern)  
> **Total Timeline:** 24 months across 4 phases

---

## Table of Contents

1. [Quick Summary](#1-quick-summary)
2. [Phase 1 — MVP (Months 1–3)](#2-phase-1--mvp-months-13)
3. [Phase 2 — Multi-Channel & Advanced AI (Months 4–7)](#3-phase-2--multi-channel--advanced-ai-months-47)
4. [Phase 3 — Enterprise SaaS (Months 8–14)](#4-phase-3--enterprise-saas-months-814)
5. [Phase 4 — AI Business OS (Months 15–24)](#5-phase-4--ai-business-os-months-1524)
6. [Full Project Structure](#6-full-project-structure)
7. [Database Schema](#7-database-schema)
8. [Tech Stack Reference](#8-tech-stack-reference)
9. [Environment Variables](#9-environment-variables)
10. [Docker Compose](#10-docker-compose)
11. [API Reference](#11-api-reference)
12. [Cost Estimates](#12-cost-estimates)
13. [Risks & Mitigations](#13-risks--mitigations)

---

## 1. Quick Summary

### What We're Building
A multi-tenant SaaS platform that deploys human-like AI agents as sales and support reps for service-based businesses (travel, clinics, restaurants, real estate, education). The AI handles lead qualification, pricing queries, objection handling, appointment booking, and human escalation — all through WhatsApp and other channels.

### Core Principle
> Your boilerplate's Clean Architecture (edge → mediator → services → repositories → di) maps **perfectly** onto an AI agent platform. This is pure extension, zero rework.

| Your Layer | AI Sales Agent Role |
|---|---|
| `edge/http/controller/` | Receives WhatsApp webhooks, REST API |
| `edge/http/routes/` | URL routing for webhooks, conversations, knowledge |
| `edge/socket/` | Real-time WebSocket for website live chat |
| `mediator/` | Routes messages to AI pipeline |
| `services/ai/` | Agent, RAG, memory, prompt builder, guardrails |
| `services/channels/` | WhatsApp, Instagram, FB channel clients |
| `repositories/` | Conversations, leads, knowledge, tenants |
| `di/container.py` | Wires OpenAI, Qdrant, AgentService |
| `configs/app_config.py` | Extended with AI + Meta + Qdrant settings |
| `workers/` *(new)* | Celery tasks for async AI inference |

---

## 2. Phase 1 — MVP (Months 1–3)

### 🎯 Goal
Live AI agent on WhatsApp for one pilot business. Customer sends a message → AI responds like a human sales rep using the business's uploaded knowledge base.

### ✅ Deliverables
- [ ] WhatsApp Business Cloud API webhook (receive + verify)
- [ ] AI agent pipeline: RAG + GPT-4o + memory
- [ ] Knowledge base ingestion (PDF, DOCX, TXT → Qdrant)
- [ ] Conversation memory (Redis hot cache)
- [ ] Human handoff system
- [ ] Human-like typing delays
- [ ] Lead scoring (passive, from conversation signals)
- [ ] Basic admin dashboard (conversations view + knowledge upload)
- [ ] Celery async task queue
- [ ] PostgreSQL schema for all core tables

---

### 2.1 Step-by-Step Build Order

#### Step 1 — Extend app_config.py

```python
# app/configs/app_config.py — add to your existing Settings class

class Settings(BaseSettings):
    # === YOUR EXISTING FIELDS (unchanged) ===
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str

    # === AI AGENT — new ===
    OPENAI_API_KEY: str
    OPENAI_MODEL: str             = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str   = "text-embedding-3-small"
    AI_TEMPERATURE: float         = 0.7
    AI_MAX_TOKENS: int            = 800
    AI_MEMORY_WINDOW: int         = 20
    AI_CONFIDENCE_THRESHOLD: float = 0.75

    # === VECTOR DATABASE ===
    QDRANT_URL: str               = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION: str        = "knowledge_base"

    # === CELERY ===
    CELERY_BROKER_URL: str        = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str    = "redis://localhost:6379/2"

    # === WHATSAPP / META ===
    META_APP_SECRET: str
    WHATSAPP_API_VERSION: str     = "v21.0"

    class Config:
        env_file = ".env"
        extra = "ignore"
```

---

#### Step 2 — Database Migrations

Create these migration files in order:

```bash
alembic revision -m "add_tenant_model"
alembic revision -m "add_conversation_models"
alembic revision -m "add_lead_model"
alembic revision -m "add_knowledge_models"
alembic upgrade head
```

**New models** (all extend your `base_model.py`):

```python
# app/models/tenant_model.py
class Tenant(BaseModel):
    __tablename__ = "tenants"
    name:                  Mapped[str]       = mapped_column(String(200))
    slug:                  Mapped[str]       = mapped_column(String(100), unique=True, index=True)
    plan:                  Mapped[str]       = mapped_column(String(50), default="free")
    is_active:             Mapped[bool]      = mapped_column(Boolean, default=True)
    ai_persona_name:       Mapped[str]       = mapped_column(String(100), default="Assistant")
    ai_config:             Mapped[dict]      = mapped_column(JSON, default=dict)
    system_prompt_override:Mapped[str|None]  = mapped_column(Text, nullable=True)
    whatsapp_phone_id:     Mapped[str|None]  = mapped_column(String(100), nullable=True)
    whatsapp_verify_token: Mapped[str|None]  = mapped_column(String(200), nullable=True)
    monthly_message_count: Mapped[int]       = mapped_column(Integer, default=0)
    monthly_token_count:   Mapped[int]       = mapped_column(Integer, default=0)
```

```python
# app/models/conversation_model.py
class Conversation(BaseModel):
    __tablename__ = "conversations"
    tenant_id:        Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    channel:          Mapped[str]       = mapped_column(String(50))  # whatsapp|instagram|fb|web
    customer_phone:   Mapped[str]       = mapped_column(String(50), index=True)
    customer_name:    Mapped[str|None]  = mapped_column(String(200), nullable=True)
    status:           Mapped[str]       = mapped_column(String(50), default="active")
    # active | escalated | resolved | closed
    assigned_agent_id:Mapped[uuid.UUID|None] = mapped_column(ForeignKey("users.id"), nullable=True)
    meta:             Mapped[dict]      = mapped_column(JSON, default=dict)

class Message(BaseModel):
    __tablename__ = "messages"
    conversation_id:  Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"), index=True)
    tenant_id:        Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    role:             Mapped[str]       = mapped_column(String(20))  # user|assistant|system
    content:          Mapped[str]       = mapped_column(Text)
    media_type:       Mapped[str|None]  = mapped_column(String(50), nullable=True)
    tokens_used:      Mapped[int|None]  = mapped_column(Integer, nullable=True)
    latency_ms:       Mapped[int|None]  = mapped_column(Integer, nullable=True)
```

```python
# app/models/lead_model.py
class Lead(BaseModel):
    __tablename__ = "leads"
    tenant_id:          Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    conversation_id:    Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"))
    customer_phone:     Mapped[str]       = mapped_column(String(50), index=True)
    customer_name:      Mapped[str|None]  = mapped_column(String(200), nullable=True)
    customer_email:     Mapped[str|None]  = mapped_column(String(200), nullable=True)
    score:              Mapped[int]       = mapped_column(Integer, default=0)  # 0-100
    stage:              Mapped[str]       = mapped_column(String(50), default="cold")
    # cold | warm | hot | qualified | converted
    qualification_data: Mapped[dict]      = mapped_column(JSON, default=dict)
```

---

#### Step 3 — Extend DI Container

```python
# app/di/container.py — add to your existing Container class

from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient
from app.services.ai.agent_service import AgentService
from app.services.ai.rag_service import RAGService
from app.services.ai.memory_service import MemoryService
from app.services.ai.prompt_builder import PromptBuilder
from app.services.ai.guardrails_service import GuardrailsService
from app.services.channels.whatsapp_channel import WhatsAppChannel
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.tenant_repository import TenantRepository
from app.mediator.message_mediator import MessageMediator

class Container(containers.DeclarativeContainer):
    # --- YOUR EXISTING PROVIDERS (unchanged) ---

    # --- AI LAYER (new) ---
    openai_client = providers.Singleton(AsyncOpenAI, api_key=config.OPENAI_API_KEY)
    qdrant_client = providers.Singleton(AsyncQdrantClient, url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY)

    rag_service     = providers.Factory(RAGService, qdrant=qdrant_client, openai=openai_client, collection=config.QDRANT_COLLECTION)
    memory_service  = providers.Factory(MemoryService, redis=redis, window=config.AI_MEMORY_WINDOW)
    prompt_builder  = providers.Singleton(PromptBuilder)
    guardrails      = providers.Singleton(GuardrailsService)

    agent_service   = providers.Factory(AgentService, rag=rag_service, memory=memory_service,
                                         prompt_builder=prompt_builder, guardrails=guardrails, openai=openai_client)

    whatsapp_channel = providers.Factory(WhatsAppChannel, api_version=config.WHATSAPP_API_VERSION, app_secret=config.META_APP_SECRET)

    tenant_repo       = providers.Factory(TenantRepository, db=db_session)
    conversation_repo = providers.Factory(ConversationRepository, db=db_session)
    lead_repo         = providers.Factory(LeadRepository, db=db_session)

    message_mediator  = providers.Factory(MessageMediator, conversation_repo=conversation_repo,
                                           tenant_repo=tenant_repo, lead_repo=lead_repo)
```

---

#### Step 4 — Webhook Route + Controller

```python
# app/edge/http/routes/webhook_route.py
from fastapi import APIRouter, Request, BackgroundTasks, Query
from app.di.container import Container
from dependency_injector.wiring import inject, Provide

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("/whatsapp/{tenant_id}")
@inject
async def whatsapp_inbound(
    tenant_id: str, request: Request, background_tasks: BackgroundTasks,
    controller=Provide[Container.webhook_controller],
):
    return await controller.handle_whatsapp(tenant_id, request, background_tasks)

@router.get("/whatsapp/{tenant_id}")
@inject
async def whatsapp_verify(
    tenant_id: str,
    hub_mode: str      = Query(alias="hub.mode"),
    hub_challenge: str = Query(alias="hub.challenge"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    controller=Provide[Container.webhook_controller],
):
    return await controller.verify_whatsapp(tenant_id, hub_mode, hub_challenge, hub_verify_token)
```

```python
# app/edge/http/controller/webhook_controller.py
class WebhookController:
    def __init__(self, message_mediator: MessageMediator, tenant_repo: TenantRepository):
        self.mediator    = message_mediator
        self.tenant_repo = tenant_repo

    async def handle_whatsapp(self, tenant_id: str, request: Request, background_tasks: BackgroundTasks):
        body = await request.body()
        sig  = request.headers.get("X-Hub-Signature-256", "")
        verify_whatsapp_signature(body, sig)   # raises 403 if invalid

        payload = WhatsAppWebhookPayload(**await request.json())

        for entry in payload.entry:
            for change in entry.changes:
                for msg in (change.value.messages or []):
                    background_tasks.add_task(          # NON-BLOCKING
                        self.mediator.handle_inbound,
                        tenant_id=tenant_id,
                        message=msg,
                        channel="whatsapp",
                    )
        return {"status": "ok"}   # Return 200 FAST

    async def verify_whatsapp(self, tenant_id, mode, challenge, verify_token):
        tenant = await self.tenant_repo.get_by_id(tenant_id)
        if verify_token != tenant.whatsapp_verify_token:
            raise HTTPException(403, "Invalid verify token")
        return PlainTextResponse(challenge)
```

---

#### Step 5 — Message Mediator

```python
# app/mediator/message_mediator.py
class MessageMediator:
    def __init__(self, conversation_repo, tenant_repo, lead_repo):
        self.conv_repo   = conversation_repo
        self.tenant_repo = tenant_repo
        self.lead_repo   = lead_repo

    async def handle_inbound(self, tenant_id: str, message: InboundMessage, channel: str):
        # 1. Get or create conversation
        conversation = await self.conv_repo.get_or_create(
            tenant_id=tenant_id, customer_phone=message.from_number, channel=channel)

        # 2. Persist raw inbound message
        await self.conv_repo.add_message(
            conversation_id=str(conversation.id), role="user",
            content=message.text or "", media_type=message.media_type)

        # 3. Skip AI if human is handling it
        if conversation.status == "escalated":
            return

        # 4. Get or create lead
        lead = await self.lead_repo.get_or_create(
            tenant_id=tenant_id, conversation_id=str(conversation.id),
            customer_phone=message.from_number)

        # 5. Queue Celery task
        process_message_task.delay(
            conversation_id=str(conversation.id), lead_id=str(lead.id),
            tenant_id=tenant_id, message_text=message.text or "",
            media_type=message.media_type, channel=channel)
```

---

#### Step 6 — Celery Workers

```python
# app/workers/celery_app.py
celery_app = Celery(
    "ai_sales_agent",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.message_processor", "app.workers.knowledge_indexer"],
)
celery_app.conf.update(
    task_serializer="json",
    task_acks_late=True,             # retry if worker crashes
    worker_prefetch_multiplier=1,    # one task at a time per worker
    task_routes={
        "app.workers.message_processor.*": {"queue": "ai"},
        "app.workers.knowledge_indexer.*": {"queue": "indexing"},
    },
)
```

```python
# app/workers/message_processor.py
@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def process_message_task(self, conversation_id, lead_id, tenant_id, message_text, media_type, channel):
    try:
        asyncio.run(_process(conversation_id, lead_id, tenant_id, message_text, media_type, channel))
    except Exception as exc:
        raise self.retry(exc=exc)

async def _process(conversation_id, lead_id, tenant_id, message_text, media_type, channel):
    tenant = await TenantRepository().get_by_id(tenant_id)

    # Handle voice/image
    if media_type == "audio":
        message_text = await transcribe_voice(message_text)
    elif media_type == "image":
        message_text = await describe_image(message_text)

    # AI pipeline
    agent = AgentService()
    response_text, confidence = await agent.process_message(
        conversation_id=conversation_id, tenant_config=tenant.ai_config, message=message_text)

    # Low confidence → escalate
    if confidence < tenant.ai_config.get("confidence_threshold", 0.75):
        await escalate_to_human(conversation_id, tenant_id)
        return

    # Update lead score
    await LeadScorer().update_from_message(lead_id, message_text, response_text)

    # Human-like delay
    await asyncio.sleep(calculate_typing_delay(response_text))

    # Send via channel
    await WhatsAppChannel().send_message(
        phone=tenant.customer_phone, message=response_text,
        phone_number_id=tenant.whatsapp_phone_id, access_token=tenant.whatsapp_token)
```

---

#### Step 7 — AI Services

```python
# app/services/ai/agent_service.py
class AgentService:
    async def process_message(self, conversation_id, tenant_config, message) -> tuple[str, float]:
        history  = await self.memory.get_history(conversation_id)
        knowledge = await self.rag.retrieve(query=message, tenant_id=tenant_config["id"], top_k=5)
        system_prompt = self.prompt_builder.build(
            persona_name=tenant_config.get("persona_name", "Assistant"),
            business_name=tenant_config.get("business_name", ""),
            tone=tenant_config.get("tone", "friendly and professional"),
            knowledge_context=knowledge,
            hard_rules=tenant_config.get("hard_rules", []),
        )
        resp = await self.llm.chat.completions.create(
            model=tenant_config.get("model", "gpt-4o"),
            messages=[{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": message}],
            temperature=tenant_config.get("temperature", 0.7),
            max_tokens=800,
        )
        raw = resp.choices[0].message.content
        safe, confidence = await self.guardrails.validate(raw, tenant_config)
        await self.memory.append(conversation_id, "assistant", safe)
        return safe, confidence
```

```python
# app/services/ai/rag_service.py
class RAGService:
    async def retrieve(self, query: str, tenant_id: str, top_k: int = 5) -> str:
        embed = await self.openai.embeddings.create(model="text-embedding-3-small", input=query)
        results = await self.qdrant.search(
            collection_name=self.collection,
            query_vector=embed.data[0].embedding,
            query_filter=Filter(must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]),
            limit=top_k, score_threshold=0.72,
        )
        if not results:
            return "No specific knowledge available for this query."
        return "\n\n".join([f"[{i+1}] {r.payload['content']}" for i, r in enumerate(results)])
```

```python
# app/services/ai/memory_service.py
class MemoryService:
    async def get_history(self, conversation_id: str) -> list[dict]:
        raw = await self.redis.get(f"conv:memory:{conversation_id}")
        return json.loads(raw) if raw else []

    async def append(self, conversation_id: str, role: str, content: str):
        history = await self.get_history(conversation_id)
        history.append({"role": role, "content": content})
        history = history[-self.window:]  # keep last N messages
        await self.redis.setex(f"conv:memory:{conversation_id}", 7200, json.dumps(history))
```

```python
# app/services/ai/prompt_builder.py
class PromptBuilder:
    def build(self, persona_name, business_name, tone, knowledge_context, hard_rules) -> str:
        rules = "\n".join(f"- {r}" for r in hard_rules)
        return f"""You are {persona_name}, a sales representative at {business_name}.
You communicate in a {tone} manner.

PERSONALITY RULES:
- Use short, natural messages (2-4 sentences max)
- Never say you are an AI; if asked, say "I am a virtual assistant"
- Ask only ONE follow-up question at a time
- Acknowledge before answering: "Great question!" or "Absolutely!"
- Never make promises not backed by the knowledge base

BUSINESS KNOWLEDGE (use only this for pricing/service questions):
{knowledge_context}

HARD RULES:
{rules}
- If you don't know, say "Let me get the exact details for you" and escalate
- Never discuss competitors or share other customers' information"""
```

```python
# app/services/ai/human_behavior_service.py
def calculate_typing_delay(response_text: str) -> float:
    CHARS_PER_SECOND = 8      # ~96 WPM
    MIN_DELAY        = 1.5
    MAX_DELAY        = 6.0
    base   = len(response_text) / CHARS_PER_SECOND
    jitter = random.uniform(-0.4, 1.0)
    return max(MIN_DELAY, min(MAX_DELAY, base + jitter))
```

---

#### Step 8 — WhatsApp Channel Client

```python
# app/services/channels/whatsapp_channel.py
class WhatsAppChannel(BaseChannel):
    async def send_message(self, phone: str, message: str, phone_number_id: str, access_token: str):
        url     = f"https://graph.facebook.com/{self.api_version}/{phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        payload = {"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"body": message}}
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
```

---

#### Step 9 — Knowledge Indexer

```python
# app/workers/knowledge_indexer.py
@celery_app.task(queue="indexing")
def index_document_task(doc_id: str, tenant_id: str, file_url: str, file_type: str):
    asyncio.run(_index(doc_id, tenant_id, file_url, file_type))

async def _index(doc_id, tenant_id, file_url, file_type):
    content = await download_file(file_url)
    text    = extract_text(content, file_type)   # pdf/docx/txt

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks   = splitter.split_text(text)

    embed_resp = await AsyncOpenAI().embeddings.create(model="text-embedding-3-small", input=chunks)
    vectors    = [e.embedding for e in embed_resp.data]

    points = [
        PointStruct(id=str(uuid4()), vector=vec,
                    payload={"tenant_id": tenant_id, "doc_id": doc_id, "content": chunk})
        for chunk, vec in zip(chunks, vectors)
    ]
    await AsyncQdrantClient().upsert(collection_name="knowledge_base", points=points)
    await update_doc_status(doc_id, "indexed", len(chunks))
```

---

#### Step 10 — Register Routes in main.py

```python
# app/main.py — extend your existing app factory
from app.edge.http.routes import webhook_route, conversation_route, knowledge_route, lead_route, tenant_route

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Existing startup...
    # New: initialize Qdrant collection
    await init_qdrant_collection()
    yield
    # Cleanup...

app = FastAPI(lifespan=lifespan)

# Existing routers (unchanged)
app.include_router(auth_route.router, prefix="/api/v1")
app.include_router(users_route.router, prefix="/api/v1")

# New AI Sales Agent routers
app.include_router(webhook_route.router,      prefix="/api/v1")
app.include_router(conversation_route.router, prefix="/api/v1")
app.include_router(knowledge_route.router,    prefix="/api/v1")
app.include_router(lead_route.router,         prefix="/api/v1")
app.include_router(tenant_route.router,       prefix="/api/v1")
```

---

#### Step 11 — Security Util Extension

```python
# app/utils/security_util.py — add to existing file
def verify_whatsapp_signature(body: bytes, signature_header: str) -> None:
    settings = get_settings()
    if not signature_header.startswith("sha256="):
        raise HTTPException(403, "Missing webhook signature")
    expected = hmac.new(settings.META_APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    received = signature_header.split("sha256=", 1)[1]
    if not hmac.compare_digest(expected, received):
        raise HTTPException(403, "Invalid webhook signature")
```

---

### 2.2 Complete AI Pipeline Flow

```
Customer sends WhatsApp message
         |
         v
[1]  POST /api/v1/webhooks/whatsapp/{tenant_id}
     Verify Meta HMAC-SHA256 signature (security_util.py)
     Return HTTP 200 immediately  ← CRITICAL: must be fast
         |
         v  (FastAPI BackgroundTask)
[2]  message_mediator.handle_inbound()
     Get/create Conversation in PostgreSQL
     Persist raw message (role=user)
     Check if escalated → skip AI if yes
     Get/create Lead record
     Queue Celery task → process_message_task.delay()
         |
         v  (Celery worker picks up from Redis queue)
[3]  workers/message_processor.py
         |
         v
[4]  Detect media type
     audio  → Whisper API transcription
     image  → GPT-4o Vision description
     text   → use as-is
         |
         v
[5]  services/ai/agent_service.py
     ├── memory_service.get_history()      → Redis (last 20 msgs, sub-ms)
     ├── rag_service.retrieve()            → Qdrant vector search (tenant-filtered)
     ├── prompt_builder.build()            → Assemble dynamic system prompt
     ├── openai.chat.completions.create()  → GPT-4o inference
     ├── guardrails_service.validate()     → Safety + confidence check
     ├── memory_service.append()           → Save response to Redis + PostgreSQL
     └── lead_scorer.update_from_message() → Update lead score + stage
         |
         v
[6]  confidence < threshold?
     YES → escalate_to_human() → notify agent → stop
     NO  → continue
         |
         v
[7]  asyncio.sleep(calculate_typing_delay())   → Human-like pause
         |
         v
[8]  whatsapp_channel.send_message()
     POST graph.facebook.com/v21.0/{phone_id}/messages
         |
         v
[9]  conversation_repo.add_message(role=assistant)
     tracking_util.log_token_cost()
     prometheus: increment ai_messages_processed
```

---

### 2.3 Human Handoff Flow

```
Trigger conditions:
├── Customer says "talk to a person" / "human agent" / "manager"
├── AI confidence < threshold on 2+ consecutive messages
├── Conversation tagged as complaint or refund
└── Lead score hits "qualified" (human closes the deal)

Flow:
1. AI sends: "Let me connect you with our team right away!"
2. conversation.status = "escalated"
3. Notification → available agents (email + dashboard alert)
4. Agent sees full conversation history in dashboard
5. Agent types → sends through same WhatsApp channel
6. Agent marks resolved → conversation.status = "resolved"
7. AI can optionally resume for follow-up
```

---

### 2.4 Lead Scoring System

```python
SIGNAL_SCORES = {
    "asks_pricing":     +20,   # "how much", "price", "cost", "rate"
    "asks_availability":+25,   # "available", "when", "date", "slot"
    "mentions_budget":  +20,   # "budget", "afford", "spend"
    "asks_to_book":     +30,   # "book", "reserve", "appointment", "buy"
    "name_provided":    +10,
    "phone_provided":   +15,
    "email_provided":   +15,
    "just_browsing":    -15,   # "just looking", "not now", "maybe later"
}

STAGES = {
    "cold":      (0,   30),
    "warm":      (31,  60),
    "hot":       (61,  85),
    "qualified": (86, 100),   # → alert human agent immediately
}
```

---

### 2.5 Phase 1 Checklist

```
Week 1-2: Foundation
  [ ] Extend app_config.py with new env vars
  [ ] Add new SQLAlchemy models
  [ ] Run Alembic migrations
  [ ] Extend DI container

Week 3-4: Webhook + Mediator
  [ ] WhatsApp webhook route + controller
  [ ] Message mediator
  [ ] Security util HMAC verification
  [ ] Docker Compose: add Qdrant + Celery services

Week 5-6: AI Pipeline
  [ ] Celery app + message_processor
  [ ] agent_service + rag_service + memory_service
  [ ] prompt_builder + guardrails_service
  [ ] human_behavior_service

Week 7-8: Knowledge + Channel
  [ ] knowledge_indexer Celery task
  [ ] knowledge_controller (upload endpoint)
  [ ] whatsapp_channel client
  [ ] Human handoff flow

Week 9-10: Dashboard + Testing
  [ ] Basic conversation list API
  [ ] Lead list API
  [ ] Integration tests: webhook → AI → WhatsApp
  [ ] Pilot business onboarding
  [ ] End-to-end live message test
```

---

## 3. Phase 2 — Multi-Channel & Advanced AI (Months 4–7)

### 🎯 Goal
Expand to Instagram, Facebook Messenger, and website chat. Add lead management, CRM integration, voice note support, and the admin analytics dashboard.

### ✅ Deliverables
- [ ] Instagram DM integration
- [ ] Facebook Messenger integration
- [ ] Website WebSocket live chat widget
- [ ] Voice note transcription (Whisper)
- [ ] Image understanding (GPT-4o Vision)
- [ ] Multi-language auto-detect
- [ ] Lead pipeline dashboard (Kanban)
- [ ] CRM sync (HubSpot / Zoho / Google Sheets)
- [ ] Appointment booking (Calendly / Cal.com)
- [ ] Conversation summary memory (for long chats)
- [ ] Analytics dashboard

---

### 3.1 Instagram DM

```python
# app/services/channels/instagram_channel.py
# Same Meta Graph API infrastructure as WhatsApp
# Add route: POST /api/v1/webhooks/instagram/{tenant_id}
class InstagramChannel(BaseChannel):
    async def send_message(self, recipient_id: str, message: str, access_token: str):
        async with httpx.AsyncClient() as c:
            await c.post(
                "https://graph.facebook.com/v21.0/me/messages",
                json={"recipient": {"id": recipient_id}, "message": {"text": message}},
                params={"access_token": access_token},
            )
```

### 3.2 Website WebSocket Chat

```python
# app/edge/socket/socket_route.py — extend existing
@router.websocket("/ws/chat/{tenant_slug}")
async def websocket_chat(websocket: WebSocket, tenant_slug: str):
    session_id = str(uuid4())
    await manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_json()
            await websocket.send_json({"type": "typing", "active": True})
            response, _ = await agent_service.process_message(
                conversation_id=session_id,
                tenant_config=await get_tenant_config(tenant_slug),
                message=data.get("message", ""),
            )
            await asyncio.sleep(calculate_typing_delay(response))
            await websocket.send_json({"type": "typing", "active": False})
            await websocket.send_json({"type": "message", "content": response})
    except WebSocketDisconnect:
        manager.disconnect(session_id)
```

### 3.3 Voice + Image Handling

```python
# In message_processor.py
async def transcribe_voice(audio_url: str) -> str:
    audio_bytes = await download_media(audio_url)
    transcript  = await AsyncOpenAI().audio.transcriptions.create(
        model="whisper-1", file=("voice.ogg", io.BytesIO(audio_bytes), "audio/ogg"))
    return transcript.text

async def describe_image(image_url: str, customer_text: str) -> str:
    resp = await AsyncOpenAI().chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": image_url}},
            {"type": "text", "text": customer_text or "What is in this image?"},
        ]}], max_tokens=500)
    return resp.choices[0].message.content
```

### 3.4 CRM Integrations

| CRM | Service File | Method |
|---|---|---|
| HubSpot | `hubspot_service.py` | REST API — create contact + deal on qualification |
| Salesforce | `salesforce_service.py` | Connected App OAuth + REST API |
| Zoho CRM | `zoho_service.py` | Zoho API v2 |
| Google Sheets | `sheets_service.py` | Sheets API v4 — append row |
| Notion | `notion_service.py` | Notion API — add to leads database |
| Custom Webhook | `webhook_crm_service.py` | POST lead JSON to tenant's endpoint |

### 3.5 Phase 2 New Files

```
app/services/channels/
  instagram_channel.py      ADD
  facebook_channel.py       ADD
  web_chat_channel.py       ADD

app/services/integrations/  ADD (new directory)
  hubspot_service.py
  zoho_service.py
  sheets_service.py
  booking_service.py        # Calendly / Cal.com

app/services/ai/
  lead_scorer.py            ADD
  conversation_summarizer.py ADD  # for long chats >20 turns
```

---

## 4. Phase 3 — Enterprise SaaS (Months 8–14)

### 🎯 Goal
Transform from monolith to production microservices. Multi-region, Kubernetes, Stripe billing, PostgreSQL RLS, white-label support, SLA guarantees.

### ✅ Deliverables
- [ ] Microservices split (12 services, each FastAPI boilerplate instance)
- [ ] Kafka event bus (replaces BackgroundTasks for inter-service communication)
- [ ] Kubernetes on AWS EKS
- [ ] PostgreSQL Row-Level Security
- [ ] Stripe billing + usage metering
- [ ] White-label dashboard per tenant
- [ ] Multi-region deployment (AWS us-east-1 + eu-west-1)
- [ ] 99.9% SLA uptime monitoring

### 4.1 Microservices Split

| Service | Owns | Kafka Topics |
|---|---|---|
| `api-gateway` | Rate limiting, auth verify, routing | — |
| `auth-service` | JWT, OAuth, API keys | `tenants.provisioned` |
| `tenant-service` | Tenant CRUD, plans, billing hooks | `tenants.*` |
| `message-router` | Inbound webhooks, signature verify | Publishes → `messages.inbound` |
| `ai-agent-service` | RAG, LLM, memory, guardrails | Consumes `messages.inbound` → Publishes `messages.outbound` |
| `knowledge-service` | Doc ingestion, chunking, Qdrant | Consumes `knowledge.index_request` |
| `channel-service` | Outbound delivery (WA/IG/FB/Web) | Consumes `messages.outbound` |
| `conversation-service` | State, history, WebSocket for dashboard | Consumes all message events |
| `lead-service` | Scoring, CRM sync, follow-up | Consumes `leads.scored` |
| `notification-service` | Escalation alerts, email, SMS | Consumes `conversations.escalated` |
| `analytics-service` | Metrics aggregation, reports | Consumes all events |
| `billing-service` | Stripe, usage metering | Consumes `billing.usage` |

### 4.2 Kafka Topics

```
ai.messages.inbound           customer message received
ai.messages.outbound          AI response ready to send
ai.leads.scored               lead score updated
ai.leads.qualified            lead hit qualified → CRM sync + alert
ai.conversations.escalated    human handoff triggered
ai.knowledge.index_request    document upload → index
ai.tenants.provisioned        new tenant → all services initialize
ai.billing.usage              tokens/messages → billing meter
```

### 4.3 PostgreSQL RLS

```sql
-- Enable Row-Level Security (upgrade from app-layer isolation)
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages      ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads         ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON conversations
  USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Set in FastAPI dependency before any query:
await session.execute(
    text("SELECT set_config('app.current_tenant', :tid, true)"),
    {"tid": str(tenant_id)}
)
```

### 4.4 Prometheus Metrics (extend existing monitoring_config.py)

```python
ai_messages_processed = Counter("ai_messages_processed_total", "Messages processed", ["tenant_id", "channel"])
ai_response_latency   = Histogram("ai_response_latency_seconds", "AI latency", ["model"], buckets=[0.5,1,2,3,5,8,10])
ai_token_cost         = Counter("ai_token_cost_total", "Tokens consumed", ["tenant_id", "model"])
ai_escalation_rate    = Counter("ai_escalations_total", "Human escalations", ["tenant_id", "reason"])
```

---

## 5. Phase 4 — AI Business OS (Months 15–24)

### 🎯 Goal
Evolve from sales agent to full AI business operating system. Multi-agent coordination, financial intelligence, document processing, workflow automation.

### ✅ Deliverables
- [ ] LangGraph multi-agent supervisor (Sales / Support / Booking / Finance / Document agents)
- [ ] QuickBooks integration (payment status, invoice confirmation)
- [ ] OCR document intelligence (AWS Textract + GPT-4o Vision)
- [ ] n8n workflow automation
- [ ] Voice AI (outbound calls via Twilio)
- [ ] ERP connectors (SAP, Odoo)

### 5.1 Multi-Agent Architecture

```python
# app/services/ai/multi_agent_service.py
from langgraph.graph import StateGraph

# Supervisor routes to specialized agents:
# SalesAgent    → pricing, packages, upselling, objections
# SupportAgent  → complaints, refunds, escalations
# BookingAgent  → calendar, appointment creation
# FinanceAgent  → payments, invoices, QuickBooks
# DocumentAgent → OCR, contracts, ID verification

workflow = StateGraph(AgentState)
workflow.add_node("supervisor", supervisor_agent)
workflow.add_node("sales",      sales_agent)
workflow.add_node("support",    support_agent)
workflow.add_node("booking",    booking_agent)
workflow.add_node("finance",    finance_agent)
workflow.add_conditional_edges("supervisor", route_to_agent)
```

### 5.2 Document Intelligence

| Document | Capability |
|---|---|
| Invoice image | GPT-4o Vision + Textract: extract amount, date, vendor, line items |
| Bank statements | Categorize transactions, confirm payment receipt |
| ID documents | KYC: extract name, DOB, ID number |
| Contracts | Summarize terms, highlight clauses, extract key dates |
| Medical reports | Explain lab values in plain language |
| Property docs | Extract specs, price, location for real estate |

---

## 6. Full Project Structure

```
FastAPI-Boiler-Plate/  (AI Sales Agent Platform)
│
├── alembic/versions/
│   ├── b4581ff37aa6_initial_script.py       # KEEP
│   ├── 0002_add_tenant_model.py              # ADD
│   ├── 0003_add_conversation_models.py       # ADD
│   ├── 0004_add_lead_model.py                # ADD
│   └── 0005_add_knowledge_models.py          # ADD
│
├── app/
│   ├── main.py                               # EXTEND
│   ├── configs/
│   │   ├── app_config.py                     # EXTEND (AI + Qdrant + Meta)
│   │   ├── cache_config.py                   # KEEP
│   │   ├── database_config.py                # KEEP
│   │   ├── logger_config.py                  # EXTEND
│   │   ├── messaging_config.py               # EXTEND (add Celery)
│   │   ├── monitoring_config.py              # EXTEND (AI metrics)
│   │   ├── ai_config.py                      # ADD
│   │   └── vector_db_config.py               # ADD
│   │
│   ├── core/
│   │   ├── slowapi_limiter.py                # KEEP
│   │   └── auth/
│   │       ├── jwt_handler.py                # ADD (tenant-scoped JWT)
│   │       └── api_key_handler.py            # ADD
│   │
│   ├── di/
│   │   ├── container.py                      # EXTEND (register AI services)
│   │   └── loader.py                         # EXTEND
│   │
│   ├── edge/
│   │   ├── http/
│   │   │   ├── controller/
│   │   │   │   ├── auth_controller.py        # KEEP
│   │   │   │   ├── webhook_controller.py     # ADD
│   │   │   │   ├── conversation_controller.py# ADD
│   │   │   │   ├── knowledge_controller.py   # ADD
│   │   │   │   ├── lead_controller.py        # ADD
│   │   │   │   └── tenant_controller.py      # ADD
│   │   │   └── routes/
│   │   │       ├── auth_route.py             # KEEP
│   │   │       ├── health_route.py           # KEEP
│   │   │       ├── users_route.py            # KEEP
│   │   │       ├── webhook_route.py          # ADD
│   │   │       ├── conversation_route.py     # ADD
│   │   │       ├── knowledge_route.py        # ADD
│   │   │       ├── lead_route.py             # ADD
│   │   │       └── tenant_route.py           # ADD
│   │   └── socket/
│   │       ├── connection_manager.py         # EXTEND (multi-tenant rooms)
│   │       ├── socket_handler.py             # EXTEND
│   │       └── socket_route.py               # EXTEND (add /ws/chat/{slug})
│   │
│   ├── mediator/
│   │   ├── auth_mediator.py                  # KEEP
│   │   ├── message_mediator.py               # ADD
│   │   └── knowledge_mediator.py             # ADD
│   │
│   ├── middlewares/
│   │   ├── auth_middleware.py                # EXTEND (inject tenant_id)
│   │   ├── exception_middleware.py           # EXTEND (LLM exceptions)
│   │   ├── logging_middleware.py             # EXTEND (correlation IDs)
│   │   ├── rate_limit_middleware.py          # KEEP
│   │   ├── request_middleware.py             # KEEP
│   │   └── security_middleware.py            # EXTEND (HMAC verify)
│   │
│   ├── models/
│   │   ├── base_model.py                     # KEEP
│   │   ├── user_model.py                     # EXTEND (tenant FK, roles)
│   │   ├── tenant_model.py                   # ADD
│   │   ├── channel_config_model.py           # ADD
│   │   ├── conversation_model.py             # ADD
│   │   ├── message_model.py                  # ADD
│   │   ├── lead_model.py                     # ADD
│   │   ├── knowledge_doc_model.py            # ADD
│   │   └── knowledge_chunk_model.py          # ADD
│   │
│   ├── repositories/
│   │   ├── base_repository.py                # KEEP
│   │   ├── user_repository.py                # KEEP
│   │   ├── tenant_repository.py              # ADD
│   │   ├── conversation_repository.py        # ADD
│   │   ├── message_repository.py             # ADD
│   │   ├── lead_repository.py                # ADD
│   │   └── knowledge_repository.py           # ADD
│   │
│   ├── schemas/
│   │   ├── auth_schema.py                    # KEEP
│   │   ├── user_schema.py                    # KEEP
│   │   ├── socket_schema.py                  # KEEP
│   │   ├── tenant_schema.py                  # ADD
│   │   ├── conversation_schema.py            # ADD
│   │   ├── message_schema.py                 # ADD
│   │   ├── lead_schema.py                    # ADD
│   │   ├── knowledge_schema.py               # ADD
│   │   └── webhook_schema.py                 # ADD
│   │
│   ├── services/
│   │   ├── auth_service.py                   # KEEP
│   │   ├── tenant_service.py                 # ADD
│   │   ├── ai/                               # FILL ALL
│   │   │   ├── agent_service.py
│   │   │   ├── rag_service.py
│   │   │   ├── memory_service.py
│   │   │   ├── prompt_builder.py
│   │   │   ├── guardrails_service.py
│   │   │   ├── lead_scorer.py
│   │   │   └── human_behavior_service.py
│   │   └── channels/                         # FILL ALL
│   │       ├── base_channel.py
│   │       ├── whatsapp_channel.py
│   │       ├── instagram_channel.py          # Phase 2
│   │       ├── facebook_channel.py           # Phase 2
│   │       └── web_chat_channel.py           # Phase 2
│   │
│   ├── utils/
│   │   ├── logger.py                         # EXTEND
│   │   ├── security_util.py                  # EXTEND (HMAC)
│   │   └── tracking_util.py                  # EXTEND (token cost)
│   │
│   └── workers/                              # ADD ENTIRE DIRECTORY
│       ├── celery_app.py
│       ├── message_processor.py
│       ├── knowledge_indexer.py
│       └── follow_up_scheduler.py
│
├── infrastructure/
│   ├── mosquitto.conf                        # KEEP
│   ├── prometheus.yml                        # EXTEND
│   └── qdrant/config.yaml                    # ADD
│
├── docker-compose.yml                        # EXTEND
└── requirements.txt                          # EXTEND
```

---

## 7. Database Schema

```
tenants
  id, name, slug, plan, is_active
  ai_persona_name, ai_config (JSON), system_prompt_override
  whatsapp_phone_id, whatsapp_verify_token
  monthly_message_count, monthly_token_count
  created_at, updated_at

users
  id, tenant_id (FK), email, hashed_password
  role (owner|admin|agent), is_active
  created_at, updated_at

channel_configs
  id, tenant_id (FK), channel_type
  credentials (encrypted JSON), is_active
  created_at, updated_at

conversations
  id, tenant_id (FK), channel
  customer_phone, customer_name, customer_email
  status (active|escalated|resolved|closed)
  assigned_agent_id (FK → users), meta (JSON)
  created_at, updated_at

messages
  id, conversation_id (FK), tenant_id (FK)
  role (user|assistant|system)
  content, media_type, media_url
  tokens_used, latency_ms
  created_at

leads
  id, tenant_id (FK), conversation_id (FK)
  customer_phone, customer_name, customer_email
  score (0-100), stage (cold|warm|hot|qualified|converted)
  qualification_data (JSON)
  created_at, updated_at

knowledge_docs
  id, tenant_id (FK), filename, file_type
  file_url, status (pending|processing|indexed|failed)
  chunk_count, created_at

knowledge_chunks
  id, doc_id (FK), tenant_id (FK)
  content, qdrant_point_id, metadata (JSON)
  created_at

audit_logs
  id, tenant_id (FK), user_id (FK)
  action, resource_type, resource_id
  ip_address, created_at
```

---

## 8. Tech Stack Reference

### Backend
| Component | Technology |
|---|---|
| Framework | FastAPI 0.115+ |
| ASGI Server | Uvicorn + Gunicorn |
| ORM | SQLAlchemy 2.0 async |
| Migrations | Alembic |
| Task Queue | Celery 5 + Redis |
| Cache | Redis 7 |
| Auth | Your existing core/auth/ |
| Rate Limiting | SlowAPI (existing) |
| HTTP Client | httpx async |
| Validation | Pydantic v2 |

### AI / ML
| Component | Technology |
|---|---|
| Primary LLM | OpenAI GPT-4o |
| Budget LLM | GPT-4o-mini (simple FAQs) |
| Fallback LLM | Claude Sonnet |
| Embeddings | text-embedding-3-small |
| Orchestration | LangChain 0.3 / LangGraph (Phase 4) |
| Vector DB | Qdrant (self-hosted → Qdrant Cloud) |
| Speech-to-Text | OpenAI Whisper API |
| Vision | GPT-4o Vision |
| OCR | AWS Textract (Phase 4) |

### Infrastructure
| Component | Technology |
|---|---|
| Cloud | AWS (ECS Fargate → EKS Phase 3) |
| Database | Amazon RDS PostgreSQL 16 |
| Cache | Amazon ElastiCache Redis 7 |
| Storage | AWS S3 + CloudFront |
| Event Bus | Amazon MSK Kafka (Phase 3) |
| CDN / DNS | Cloudflare |
| Monitoring | Prometheus + Grafana (existing infra/) |
| CI/CD | GitHub Actions |

---

## 9. Environment Variables

```bash
# .env (extend your existing .env.example)

# === YOUR EXISTING VARS (unchanged) ===
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/platform
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key

# === AI ===
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
AI_TEMPERATURE=0.7
AI_MAX_TOKENS=800
AI_MEMORY_WINDOW=20
AI_CONFIDENCE_THRESHOLD=0.75

# === VECTOR DB ===
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=                       # leave empty for local
QDRANT_COLLECTION=knowledge_base

# === CELERY ===
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# === WHATSAPP / META ===
META_APP_SECRET=your-meta-app-secret
WHATSAPP_API_VERSION=v21.0

# === AWS (for document storage) ===
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_BUCKET=ai-platform-docs
AWS_REGION=us-east-1
```

---

## 10. Docker Compose

```yaml
# docker-compose.yml — append to existing services section

services:
  # === YOUR EXISTING SERVICES (unchanged) ===
  # app, db, redis, mosquitto, prometheus ...

  # === NEW: Celery AI Worker ===
  celery-worker:
    build: .
    command: celery -A app.workers.celery_app worker -Q ai -l info -c 4
    env_file: .env
    environment:
      - QDRANT_URL=http://qdrant:6333
    depends_on: [db, redis, qdrant]
    restart: unless-stopped

  # === NEW: Celery Indexing Worker ===
  celery-indexer:
    build: .
    command: celery -A app.workers.celery_app worker -Q indexing -l info -c 2
    env_file: .env
    depends_on: [db, redis, qdrant]

  # === NEW: Celery Beat (scheduled tasks) ===
  celery-beat:
    build: .
    command: celery -A app.workers.celery_app beat -l info
    env_file: .env
    depends_on: [redis]

  # === NEW: Qdrant Vector DB ===
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped

  # === NEW: Flower (Celery UI) ===
  flower:
    image: mher/flower
    command: celery --broker=${CELERY_BROKER_URL} flower
    ports:
      - "5555:5555"
    depends_on: [redis]

volumes:
  qdrant_data:
  # ... your existing volumes ...
```

---

## 11. API Reference

### Webhooks
```
POST   /api/v1/webhooks/whatsapp/{tenant_id}   Receive WhatsApp messages
GET    /api/v1/webhooks/whatsapp/{tenant_id}   Verify webhook (Meta requirement)
POST   /api/v1/webhooks/instagram/{tenant_id}  Phase 2
POST   /api/v1/webhooks/facebook/{tenant_id}   Phase 2
```

### Conversations
```
GET    /api/v1/conversations                   List conversations (tenant-scoped)
GET    /api/v1/conversations/{id}              Get single conversation + messages
POST   /api/v1/conversations/{id}/takeover     Human agent takes over (AI pauses)
POST   /api/v1/conversations/{id}/release      Return conversation to AI
POST   /api/v1/conversations/{id}/messages     Send message as agent
```

### Knowledge Base
```
POST   /api/v1/knowledge/upload                Upload document (PDF/DOCX/TXT)
GET    /api/v1/knowledge/docs                  List all documents
DELETE /api/v1/knowledge/docs/{id}             Delete + remove from Qdrant
POST   /api/v1/knowledge/docs/{id}/reindex     Re-index document
```

### Leads
```
GET    /api/v1/leads                           List leads with filters
GET    /api/v1/leads/{id}                      Get lead detail
PATCH  /api/v1/leads/{id}/stage               Update lead stage manually
```

### Tenants
```
POST   /api/v1/tenants                         Create new tenant (onboarding)
GET    /api/v1/tenants/{id}                    Get tenant settings
PATCH  /api/v1/tenants/{id}/ai-config         Update AI persona + settings
```

### WebSocket
```
WS     /ws/chat/{tenant_slug}                  Website live chat (Phase 2)
```

---

## 12. Cost Estimates

### Phase 1 — MVP (5 tenants, ~10K messages/month)

| Resource | Est. Cost / Month |
|---|---|
| AWS ECS Fargate (API + Celery) | $50–90 |
| RDS PostgreSQL db.t3.medium | $50 |
| ElastiCache Redis | $20 |
| Qdrant (self-hosted ECS) | $25 |
| S3 + CloudFront | $5–10 |
| OpenAI API (10K messages, avg 600 tokens) | $35–70 |
| WhatsApp Business API | $0 (first 1000 conv/month free) |
| **Total** | **~$185–265 / month** |

### Phase 2 — Growth (50 tenants, ~500K messages/month)

| Resource | Est. Cost / Month |
|---|---|
| AWS ECS Fargate (scaled) | $400–600 |
| RDS PostgreSQL Multi-AZ | $220 |
| ElastiCache Redis cluster | $90 |
| Qdrant Cloud | $120–200 |
| OpenAI API | $1,500–3,000 |
| WhatsApp + Meta channels | $200–500 |
| CDN, monitoring, storage | $80–120 |
| **Total** | **~$2,600–4,700 / month** |

> **Cost tip:** Use GPT-4o-mini for simple FAQ intents (70% cheaper). Cache frequent queries in Redis with a 1-hour TTL. Set monthly token budgets per tenant plan.

---

## 13. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| AI hallucination | RAG grounds all responses. Confidence threshold check. "I don't know" fallback triggers escalation. |
| LLM latency > 8s | Celery async — customer gets typing indicator while AI processes. Fast intent classifier for simple queries. |
| WhatsApp policy ban | Template-only outbound. 24h window enforced in code. No bulk sending. Meta compliance review before launch. |
| Celery task loss | `task_acks_late=True` ensures retry on crash. Redis AOF persistence enabled. |
| Token cost overrun | Per-tenant monthly budgets. Model routing. Redis cache for repeat queries. |
| Tenant data leak | `tenant_id` filter on every DB query. Phase 3: PostgreSQL RLS. DI container prevents cross-wiring. |
| Knowledge staleness | Auto re-index on document update. Weekly scheduled freshness check. |
| Webhook not received | Always return 200 fast. Idempotency key on processing to skip duplicate deliveries. |
| Low AI quality | RAGAS evaluation weekly. Prompt version tracking. Easy rollback to previous prompt version. |

---

## New pip Dependencies

```txt
# Add to requirements.txt

# AI
openai>=1.51.0
langchain>=0.3.0
langchain-openai>=0.2.0
langchain-community>=0.3.0

# Vector DB
qdrant-client>=1.11.0

# Task Queue
celery[redis]>=5.4.0
flower>=2.0.0

# Document Processing
pypdf2>=3.0.0
python-docx>=1.1.0
openpyxl>=3.1.0
tiktoken>=0.7.0
langdetect>=1.0.9

# Crypto (for encrypting channel credentials)
cryptography>=43.0.0
```

---

*Built on FastAPI Boilerplate — Clean Architecture — Extension, not rewrite.*
