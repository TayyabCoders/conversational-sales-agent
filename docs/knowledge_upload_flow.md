# End-to-End Flow: POST /knowledge/knowledge/upload

This document provides a comprehensive analysis of the complete flow for uploading a knowledge document, including chunking, embedding, and database storage.

## Overview

The knowledge upload process follows an asynchronous architecture pattern:
1. **Synchronous Phase**: File upload → Cloud storage → Database record creation → Message queue publishing
2. **Asynchronous Phase**: Message consumption → Text extraction → Chunking → Embedding → Vector storage

---

## Complete Flow Diagram

```
POST /knowledge/knowledge/upload
    ↓
[Route Layer] knowledge_route.py
    ↓
[Controller Layer] knowledge_controller.py
    ↓
[Mediator Layer] knowledge_mediator.py
    ↓
[Service Layer] knowledge_service.py
    ↓
[Repository Layer] knowledge_repository.py
    ↓
[Storage Utility] storage_util.py (Cloudinary)
    ↓
[Message Queue] RabbitMQ
    ↓
[Worker/Consumer] knowledge_consumer.py
    ↓
[Database] PostgreSQL (pgvector)
```

---

## Detailed Flow Analysis

### 1. Route Layer
**File**: `app/edge/http/routes/knowledge_route.py`

**Function**: `upload_document()`
```python
@router.post("/knowledge/upload")
@inject
async def upload_document(
    file: UploadFile = File(...),
    controller: KnowledgeController = Depends(Provide["knowledge_controller"]),
):
    return await controller.upload(file)
```

**Purpose**: 
- Defines the POST endpoint `/knowledge/upload`
- Receives the uploaded file via FastAPI's `UploadFile`
- Uses dependency injection to get the `KnowledgeController` instance
- Delegates to the controller's `upload()` method

---

### 2. Controller Layer
**File**: `app/edge/http/controller/knowledge_controller.py`

**Class**: `KnowledgeController`

**Method**: `upload()`
```python
async def upload(self, file: UploadFile):
    # 1. Validate file type
    ext = file.filename.split(".")[-1].lower()
    if ext not in ALLOWED_TYPES:
        raise HTTPException(400, f"File type .{ext} not supported. Allowed: {ALLOWED_TYPES}")
    
    # 2. Delegate to mediator
    doc = await self.knowledge_mediator.ingest_document(file=file, file_type=ext)
    
    # 3. Return response
    return {"message": "Document uploaded and indexing started.", "doc_id": str(doc.id)}
```

**Allowed File Types**: `{"pdf", "docx", "txt", "csv"}`

**Purpose**:
- Validates the file extension
- Calls the mediator to handle document ingestion
- Returns immediate response with document ID (indexing happens asynchronously)

---

### 3. Mediator Layer
**File**: `app/mediator/knowledge_mediator.py`

**Class**: `KnowledgeMediator`

**Method**: `ingest_document()`
```python
async def ingest_document(self, file: UploadFile, file_type: str):
    # 1. Upload raw file to Cloudinary
    file_bytes = await file.read()
    file_url = await upload_to_cloud(file_bytes, file.filename)
    
    # 2. Create DB record (status=pending) via service
    doc = await self.knowledge_service.create_document(
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
    
    return doc
```

**Purpose**:
- Orchestrates the document ingestion process
- Uploads file to cloud storage (Cloudinary)
- Creates database record with status "pending"
- Publishes message to RabbitMQ for asynchronous processing

---

### 4. Storage Utility (Cloudinary)
**File**: `app/utils/storage_util.py`

**Function**: `upload_to_cloud()`
```python
async def upload_to_cloud(file_bytes: bytes, filename: str) -> str:
    # 1. Configure Cloudinary from environment variables
    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret
    )
    
    # 2. Upload file to Cloudinary
    upload_result = cloudinary.uploader.upload(
        file_bytes,
        public_id=f"uploads/{filename}",
        resource_type="auto"
    )
    
    # 3. Return secure URL
    return upload_result.get("secure_url")
```

**Purpose**:
- Uploads file bytes to Cloudinary cloud storage
- Returns a publicly accessible URL for the file
- Runs synchronously in a thread pool to avoid blocking

---

### 5. Service Layer
**File**: `app/services/knowledge_service.py`

**Class**: `KnowledgeService`

**Method**: `create_document()`
```python
async def create_document(
    self,
    filename: str,
    file_type: str,
    file_url: str,
) -> Dict[str, Any]:
    doc = await self.knowledge_repository.create(
        filename=filename,
        file_type=file_type,
        file_url=file_url,
    )
    
    # Record business event
    self.prometheus.record_business_event("knowledge_document_create", "success")
    
    return doc
```

**Purpose**:
- Business logic layer for knowledge documents
- Delegates database operations to repository
- Records metrics for monitoring

---

### 6. Repository Layer
**File**: `app/repositories/knowledge_repository.py`

**Class**: `KnowledgeRepository`

**Method**: `create()`
```python
async def create(
    self,
    filename: str,
    file_type: str,
    file_url: str,
) -> KnowledgeDoc:
    doc_data = {
        "filename": filename,
        "file_type": file_type,
        "file_url": file_url,
        "status": "pending",
        "chunk_count": 0,
    }
    doc = await super().create(doc_data)
    return doc
```

**Purpose**:
- Handles database operations for knowledge documents
- Creates record in `knowledge_docs` table with initial status "pending"

---

### 7. Database Model
**File**: `app/models/knowledge_doc_model.py`

**Table**: `knowledge_docs`

```python
class KnowledgeDoc(Base):
    __tablename__ = "knowledge_docs"
    
    id: UUID (primary key)
    filename: String(300)
    file_type: String(20)  # pdf | docx | txt | csv
    file_url: String(500)
    status: String(50)  # pending | processing | indexed | failed
    chunk_count: Integer (default=0)
    created_at: DateTime
    updated_at: DateTime
```

**Purpose**:
- SQLAlchemy model for knowledge documents
- Tracks document metadata and processing status

---

### 8. Message Queue (RabbitMQ)
**Exchange**: `ai`
**Routing Key**: `ai.knowledge`
**Queue**: `ai.knowledge.queue`

**Message Payload**:
```json
{
    "doc_id": "uuid",
    "file_url": "https://cloudinary-url...",
    "file_type": "pdf"
}
```

**Purpose**:
- Decouples the upload process from the indexing process
- Enables asynchronous processing of documents
- Provides reliability through message persistence

---

### 9. Worker/Consumer Layer
**File**: `app/workers/knowledge_consumer.py`

**Startup Function**: `start_knowledge_consumer()`
```python
async def start_knowledge_consumer(rabbitmq: RabbitMQClient) -> None:
    await rabbitmq.consume(
        exchange     = "ai",
        queue_name   = "ai.knowledge.queue",
        routing_keys = ["ai.knowledge"],
        callback     = handle_index_request,
    )
```

**Called from**: `app/main.py` during application startup (line 60)

---

### 10. Index Request Handler
**File**: `app/workers/knowledge_consumer.py`

**Function**: `handle_index_request()`
```python
async def handle_index_request(payload: dict) -> None:
    await _index(
        doc_id    = payload["doc_id"],
        file_url  = payload["file_url"],
        file_type = payload["file_type"],
    )
```

**Purpose**:
- RabbitMQ message callback
- Delegates to the `_index()` function for actual processing

---

### 11. Main Indexing Logic
**File**: `app/workers/knowledge_consumer.py`

**Function**: `_index()`

This is where the actual chunking, embedding, and storage happens:

```python
async def _index(doc_id: str, file_url: str, file_type: str) -> None:
    repo = KnowledgeRepository()
    
    # 1. Update status to "processing"
    await repo.update_status(doc_id, "processing")
    
    # 2. Download file from Cloudinary
    async with httpx.AsyncClient() as client:
        resp = await client.get(file_url)
        content = resp.content
    
    # 3. Extract text based on file type
    extracted_text = _extract_text(content, file_type)
    
    # 4. Chunk with overlap
    splitter = RecursiveCharacterTextSplitter(
        chunk_size    = 500,
        chunk_overlap = 50,
        separators    = ["\n\n", "\n", ". ", " "],
    )
    chunks = splitter.split_text(extracted_text)
    
    # 5. Embed all chunks using configured provider
    vectors = []
    if use_gemini and gemini_client:
        import google.generativeai as genai
        for chunk in chunks:
            embed_resp = genai.embed_content(
                model=settings.GEMINI_EMBEDDING_MODEL,
                content=chunk,
                task_type="retrieval_document"
            )
            vectors.append(embed_resp['embedding'])
    elif openai_client:
        for chunk in chunks:
            embed_resp = await openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=chunk,
            )
            vectors.append(embed_resp.data[0].embedding)
    
    # 6. Insert chunks + vectors into PostgreSQL (pgvector)
    embedding_column = "embedding_gemini" if use_gemini else "embedding"
    async with db.get_session("write") as session:
        for chunk, vec in zip(chunks, vectors):
            vector_str = "[" + ",".join(str(v) for v in vec) + "]"
            await session.execute(
                text(f"""
                    INSERT INTO knowledge_chunks
                        (id, doc_id, content, {embedding_column}, embedding_provider, created_at)
                    VALUES
                        ($1, $2, $3, $4::vector, $5, NOW())
                """),
                (str(uuid.uuid4()), doc_id, chunk, vector_str, "gemini" if use_gemini else "openai"),
            )
        await session.commit()
    
    # 7. Mark as indexed
    await repo.update_status(doc_id, "indexed", chunk_count=len(chunks))
```

---

### 12. Text Extraction
**File**: `app/workers/knowledge_consumer.py`

**Function**: `_extract_text()`
```python
def _extract_text(content: bytes, file_type: str) -> str:
    if file_type == "pdf":
        reader = pypdf.PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() for page in reader.pages)
    elif file_type == "docx":
        from docx import Document
        doc = Document(io.BytesIO(content))
        return "\n".join(para.text for para in doc.paragraphs)
    else:
        return content.decode("utf-8", errors="ignore")
```

**Purpose**:
- Extracts plain text from various file formats
- Supports PDF, DOCX, TXT, and CSV files

---

### 13. Chunking Strategy
**Library**: `langchain_text_splitters.RecursiveCharacterTextSplitter`

**Configuration**:
- `chunk_size`: 500 characters
- `chunk_overlap`: 50 characters
- `separators`: `["\n\n", "\n", ". ", " "]`

**Purpose**:
- Splits large text into manageable chunks
- Uses recursive splitting with multiple separators for better semantic boundaries
- Overlap ensures context continuity between chunks

---

### 14. Embedding Generation
**Providers**: OpenAI or Gemini (configurable via `USE_GEMINI` setting)

**OpenAI**:
- Model: `text-embedding-3-small`
- Dimensions: 1536
- Column: `embedding`

**Gemini**:
- Model: `text-embedding-004` (configurable via `GEMINI_EMBEDDING_MODEL`)
- Dimensions: 768
- Column: `embedding_gemini`

**Purpose**:
- Converts text chunks into vector representations
- Enables semantic search and similarity matching

---

### 15. Vector Storage
**File**: `app/workers/knowledge_consumer.py`

**Database**: PostgreSQL with pgvector extension

**Table**: `knowledge_chunks`

```python
class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    
    id: UUID (primary key)
    doc_id: UUID (foreign key to knowledge_docs)
    content: Text
    embedding: vector (1536) - OpenAI
    embedding_gemini: vector (768) - Gemini
    embedding_provider: String
    created_at: DateTime
    updated_at: DateTime
```

**Insertion**:
```python
INSERT INTO knowledge_chunks
    (id, doc_id, content, embedding, embedding_provider, created_at)
VALUES
    ($1, $2, $3, $4::vector, $5, NOW())
```

**Purpose**:
- Stores text chunks with their vector embeddings
- Uses pgvector for efficient similarity search
- Supports multiple embedding providers

---

### 16. Status Updates
**File**: `app/repositories/knowledge_repository.py`

**Method**: `update_status()`
```python
async def update_status(self, doc_id: str, status: str, chunk_count: int = 0) -> None:
    update_data = {"status": status}
    if chunk_count > 0:
        update_data["chunk_count"] = chunk_count
    await self.update(doc_id, update_data)
```

**Status Flow**:
1. `pending` - Initial state after upload
2. `processing` - Worker started indexing
3. `indexed` - Successfully completed
4. `failed` - Error during indexing

---

## Application Startup

**File**: `app/main.py`

**Lifespan Context Manager** (lines 18-72):
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize Database Connection
    database = container.resolve('database')
    await database.connect()
    
    # 2. Initialize Models (create tables)
    if settings.DB_AUTO_MIGRATE:
        await initialize_models(database)
    
    # 3. Connect RabbitMQ and start consumers
    rabbitmq = container.resolve('rabbitmq')
    await rabbitmq.connect()
    
    from app.workers.knowledge_consumer import start_knowledge_consumer
    
    # Start consumer as background task
    asyncio.create_task(start_knowledge_consumer(rabbitmq))
    
    yield
    
    # Shutdown logic
    await rabbitmq.disconnect()
    await database.disconnect()
```

**Purpose**:
- Initializes database and RabbitMQ connections on startup
- Starts the knowledge consumer as a background task
- Ensures proper cleanup on shutdown

---

## RAG Service (Retrieval)

**File**: `app/services/ai/rag_service.py`

**Purpose**: Uses the stored embeddings for semantic search

**Method**: `retrieve()`
```python
async def retrieve(self, query: str, top_k: int = 5) -> str:
    # 1. Embed the query
    query_vector = embed_query(query)
    
    # 2. Cosine similarity search using pgvector
    sql = text(f"""
        SELECT content,
               1 - (embedding <=> :query_vec::vector) AS similarity
        FROM   knowledge_chunks
        WHERE  1 - (embedding <=> :query_vec::vector) > 0.72
        ORDER  BY embedding <=> :query_vec::vector
        LIMIT  :top_k
    """)
    
    # 3. Return relevant chunks
    return format_chunks(results)
```

**Purpose**:
- Retrieves relevant knowledge chunks based on semantic similarity
- Uses cosine distance (`<=>` operator) for similarity calculation
- Threshold of 0.72 filters out low-quality matches

---

## Summary

### Synchronous Flow (Immediate Response)
1. **Route** receives file upload
2. **Controller** validates file type
3. **Mediator** uploads to Cloudinary
4. **Service** creates database record (status: pending)
5. **Mediator** publishes message to RabbitMQ
6. **Response** returned to client with doc_id

### Asynchronous Flow (Background Processing)
1. **Consumer** receives message from RabbitMQ
2. **Worker** downloads file from Cloudinary
3. **Worker** extracts text from file
4. **Worker** chunks text (500 chars, 50 overlap)
5. **Worker** generates embeddings (OpenAI or Gemini)
6. **Worker** stores chunks + vectors in PostgreSQL (pgvector)
7. **Worker** updates document status to "indexed"

### Key Technologies
- **FastAPI**: Web framework
- **Cloudinary**: Cloud file storage
- **RabbitMQ**: Message queue for async processing
- **PostgreSQL + pgvector**: Vector database
- **LangChain**: Text chunking
- **OpenAI/Gemini**: Embedding generation
- **SQLAlchemy**: ORM

### Database Tables
1. **knowledge_docs**: Document metadata and status
2. **knowledge_chunks**: Text chunks with vector embeddings

### Status Transitions
`pending` → `processing` → `indexed` (or `failed`)

---

## File Reference Summary

| Layer | File | Key Functions |
|-------|------|---------------|
| Route | `app/edge/http/routes/knowledge_route.py` | `upload_document()` |
| Controller | `app/edge/http/controller/knowledge_controller.py` | `upload()` |
| Mediator | `app/mediator/knowledge_mediator.py` | `ingest_document()` |
| Service | `app/services/knowledge_service.py` | `create_document()` |
| Repository | `app/repositories/knowledge_repository.py` | `create()`, `update_status()` |
| Storage | `app/utils/storage_util.py` | `upload_to_cloud()` |
| Worker | `app/workers/knowledge_consumer.py` | `start_knowledge_consumer()`, `handle_index_request()`, `_index()`, `_extract_text()` |
| Model | `app/models/knowledge_doc_model.py` | `KnowledgeDoc`, `KnowledgeChunk` |
| Schema | `app/schemas/knowledge_schema.py` | `KnowledgeDocResponse` |
| RAG | `app/services/ai/rag_service.py` | `retrieve()` |
| Main | `app/main.py` | `lifespan()` (starts consumer) |
