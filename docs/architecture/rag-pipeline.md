# RAG Pipeline — End-to-End Documentation

## Overview

This project implements a Retrieval-Augmented Generation (RAG) system for a WhatsApp sales agent. Documents are uploaded, chunked, embedded, and stored in PostgreSQL + pgvector. When a customer sends a message, the agent retrieves relevant knowledge before generating a response.

---

## Architecture at a Glance

```
DOCUMENT UPLOAD                        CUSTOMER MESSAGE
      │                                       │
      ▼                                       ▼
POST /knowledge/upload          POST /webhooks/whatsapp
      │                                       │
      ▼                                       ▼
Upload to Cloudinary            Persist message + publish
Create knowledge_docs row       to RabbitMQ "ai.messages"
Publish to RabbitMQ                            │
"ai.knowledge"                                 ▼
      │                          ai_message_consumer
      ▼                                _process()
knowledge_consumer                             │
    _index()                                   ▼
      │                            RAGService.retrieve()
      ▼                            ┌─ embed query
Download → Extract text            └─ cosine search pgvector
Chunk (500 / 50 overlap)                       │
Embed (OpenAI / Gemini)                        ▼
INSERT knowledge_chunks            AgentService.process_message()
UPDATE status = "indexed"          Build prompt + LLM + guardrails
                                               │
                                               ▼
                                   Send WhatsApp reply
```

---

## Step-by-Step Flow

### 1. Document Upload

**Endpoint:** `POST /api/v1/knowledge/knowledge/upload`

| Layer | File | Function |
|-------|------|----------|
| Route | `app/edge/http/routes/knowledge_route.py` | `upload_document()` |
| Controller | `app/controllers/knowledge_controller.py` | `KnowledgeController.upload()` |
| Mediator | `app/mediator/knowledge_mediator.py` | `KnowledgeMediator.ingest_document()` |
| Service | `app/services/knowledge_service.py` | `KnowledgeService.create_document()` |

**What happens:**
1. Controller validates file type (pdf, docx, txt, csv)
2. Mediator uploads file bytes to Cloudinary → gets back `file_url`
3. Creates a `knowledge_docs` row with `status="pending"`
4. Publishes a message to RabbitMQ:

```python
await self.rabbitmq.publish(
    exchange="ai",
    routing_key="ai.knowledge",
    message={"doc_id": str(doc.id), "file_url": file_url, "file_type": file_type},
)
```

---

### 2. Background Indexing Worker

**File:** `app/workers/knowledge_consumer.py`

Started at app startup in `app/main.py` lifespan as an `asyncio.create_task()`.

Listens on: exchange `"ai"`, queue `"ai.knowledge.queue"`, routing key `"ai.knowledge"`

**`_index(doc_id, file_url, file_type)`** — core function:

```
1. Download file from Cloudinary URL
2. Extract text:
   - PDF  → pypdf PdfReader
   - DOCX → python-docx Document
   - TXT  → decode UTF-8
   - CSV  → csv.reader rows joined
3. Chunk with RecursiveCharacterTextSplitter
   - chunk_size=500, chunk_overlap=50
4. Embed each chunk:
   - OpenAI  → text-embedding-3-small  (1536 dims) → column: embedding
   - Gemini  → GEMINI_EMBEDDING_MODEL  (3072 dims) → column: embedding_gemini
5. INSERT rows into knowledge_chunks
6. UPDATE knowledge_docs SET status="indexed", chunk_count=N
```

On any error: `UPDATE knowledge_docs SET status="failed"`

---

### 3. Database Schema

**Table: `knowledge_docs`**

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| filename | String(300) | |
| file_type | String(20) | pdf / docx / txt / csv |
| file_url | String(500) | Cloudinary URL |
| status | String(50) | pending → processing → indexed → failed |
| chunk_count | Integer | Set after indexing |
| created_at | DateTime | |
| updated_at | DateTime | |

**Table: `knowledge_chunks`**

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| doc_id | UUID FK | → knowledge_docs.id |
| content | Text | Raw chunk text |
| embedding | vector(1536) | OpenAI embeddings |
| embedding_gemini | vector(3072) | Gemini embeddings |
| embedding_provider | String(20) | "openai" or "gemini" |
| created_at | DateTime | |

**Indexes:**
- `knowledge_chunks_embedding_idx` — IVFFlat on `embedding` (cosine, OpenAI 1536-dim)
- `ix_knowledge_chunks_doc_id` — B-tree on `doc_id`
- `embedding_gemini` has **no ANN index** — pgvector's IVFFlat and HNSW both cap at 2000 dims; 3072-dim queries use exact sequential scan

---

### 4. Alembic Migration Chain

```
base
 └─ 94947e70a876   Create knowledge_docs + knowledge_chunks tables
     └─ 4fa97bb67d7c   Enable pgvector, add embedding vector(1536), IVFFlat index
         └─ gemini_001  (add_gemini_embedding_support.py)
         │              Add embedding_gemini vector(768), embedding_provider, IVFFlat index
             └─ gemini_002  (update_embedding_gemini_to_3072.py)
                            Drop 768-dim index, resize embedding_gemini → vector(3072)
                            (no ANN index — exceeds pgvector 2000-dim limit)
```

Run with: `.\.venv\Scripts\alembic.exe upgrade head`

---

### 5. RAG Retrieval Service

**File:** `app/services/ai/rag_service.py` — `class RAGService`

#### `retrieve(query, top_k=5)` → `str`

Called inside `AgentService.process_message()` before LLM inference.

```python
# 1. Embed the query with the same model used at indexing time
embed_resp = genai.embed_content(
    model=settings.GEMINI_EMBEDDING_MODEL,
    content=query,
    task_type="retrieval_document"
)
query_vector = embed_resp['embedding']

# 2. Cosine similarity search on pgvector
SELECT content,
       1 - (embedding_gemini <=> :query_vec::vector) AS similarity
FROM   knowledge_chunks
WHERE  1 - (embedding_gemini <=> :query_vec::vector) > 0.72
ORDER  BY embedding_gemini <=> :query_vec::vector
LIMIT  :top_k
```

Returns the top-K chunks formatted as a numbered list, or `"No relevant knowledge found for this query."` if nothing exceeds the 0.72 similarity threshold.

#### `embed_text(text_input)` → `list[float]`

Utility used by the knowledge consumer to embed individual chunks before insertion.

---

### 6. Agent Service — Where RAG Plugs In

**File:** `app/services/ai/agent_service.py` — `process_message()`

```
1.  Load conversation history from Redis
         ↓
2.  RAG retrieval  ←── THIS IS WHERE RAG RUNS
    knowledge = await self.rag.retrieve(query=message, top_k=5)
         ↓
3.  Build system prompt
    Includes: persona, business rules, tone, + knowledge_context from RAG
         ↓
4.  LLM inference (OpenAI GPT-4o  OR  Gemini)
    [system_prompt + history + user_message]
         ↓
5.  Guardrails validation
    GuardrailsService.validate(response, config)
         ↓
6.  Save response to Redis memory
         ↓
7.  Return (response, confidence_score)
```

---

### 7. Inbound Message Flow (WhatsApp → AI Response)

**File:** `app/workers/ai_message_consumer.py` — `_process()`

```
POST /webhooks/whatsapp
        │
        ▼
WebhookController.handle_whatsapp()
        │
        ▼
MessageMediator.handle_inbound()
  ├─ Upsert Conversation + Lead (DB)
  ├─ Persist customer message (DB)
  ├─ Skip if conversation escalated to human
  └─ Publish to RabbitMQ "ai.messages"
        │
        ▼  (async, background task)
ai_message_consumer._process()
  ├─ Check escalation trigger (GuardrailsService)
  ├─ Init RAGService(db, openai/gemini client, use_gemini flag)
  ├─ Init AgentService(rag, memory, prompt_builder, guardrails)
  ├─ AgentService.process_message()  ← RAG + LLM here
  ├─ Check confidence threshold → escalate to human if low
  ├─ Update lead score
  ├─ Simulate human typing delay
  ├─ Send reply via WhatsApp Cloud API
  └─ Persist AI message (DB)
```

---

### 8. App Startup — Worker Registration

**File:** `app/main.py` — `lifespan(app)`

```python
# Startup
await database.connect()
await initialize_models()          # create_all for base tables (not Alembic)
await rabbitmq.connect()

asyncio.create_task(start_knowledge_consumer(rabbitmq))   # document indexing
asyncio.create_task(start_ai_message_consumer(rabbitmq))  # AI responses

# Shutdown
await rabbitmq.disconnect()
await database.disconnect()
```

---

## Configuration Reference

All values read from `.env` via `app/configs/app_config.py` (`pydantic-settings`).

| Key | Default | Effect |
|-----|---------|--------|
| `USE_GEMINI` | `false` | Switch embedding + LLM provider to Gemini |
| `GEMINI_API_KEY` | — | Google API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` | LLM model for chat |
| `GEMINI_EMBEDDING_MODEL` | `models/embedding-001` | Embedding model |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o` | LLM model for chat |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `AI_CONFIDENCE_THRESHOLD` | `0.75` | Below this → escalate to human |
| `AI_MEMORY_WINDOW` | `20` | Messages kept in Redis per conversation |
| `DB_AUTO_MIGRATE` | `true` | Run `create_all` on startup (not Alembic) |

---

## Known Constraints

| Constraint | Detail |
|-----------|--------|
| pgvector ANN index limit | Both IVFFlat and HNSW cap at 2000 dims. The `embedding_gemini vector(3072)` column has no ANN index — queries do an exact scan. Fine for small knowledge bases. |
| google-generativeai SDK | Version `0.8.6` uses the deprecated `v1beta` gRPC API. Only `models/embedding-001` (768-dim) and `models/gemini-embedding-001` (3072-dim) are available on this endpoint. `text-embedding-004` and `gemini-embedding-004` return 404. |
| DB_AUTO_MIGRATE | Only runs `Base.metadata.create_all`. Alembic migrations must be run manually: `.\.venv\Scripts\alembic.exe upgrade head` |
