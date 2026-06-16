# OpenAI to Gemini Migration Plan

## Overview
This document provides a comprehensive end-to-end migration plan to transition the conversational sales agent from OpenAI to Google Gemini (Generative AI).

## Current OpenAI Usage Analysis

### Files Using OpenAI
1. **app/services/ai/rag_service.py** - Embeddings (text-embedding-3-small)
2. **app/services/ai/agent_service.py** - Chat completions (gpt-4o)
3. **app/workers/ai_message_consumer.py** - Chat completions, audio transcription (whisper-1), image description (gpt-4o)
4. **app/workers/knowledge_consumer.py** - Embeddings (text-embedding-3-small)
5. **app/configs/app_config.py** - Configuration settings
6. **app/di/loader.py** - DI container registration
7. **env.example** - Environment variables

### OpenAI Features Used
- Text embeddings (text-embedding-3-small)
- Chat completions (gpt-4o)
- Audio transcription (whisper-1) - currently commented out
- Image description/vision (gpt-4o) - currently commented out

## Gemini Equivalent Mapping

| OpenAI Feature | OpenAI Model | Gemini Equivalent | Gemini Model |
|----------------|-------------|-------------------|--------------|
| Chat Completions | gpt-4o | Chat Completions | gemini-1.5-pro or gemini-1.5-flash |
| Text Embeddings | text-embedding-3-small | Text Embeddings | text-embedding-004 |
| Audio Transcription | whisper-1 | Audio Processing | gemini-1.5-pro (multimodal) |
| Image/Vision | gpt-4o | Vision/Multimodal | gemini-1.5-pro or gemini-1.5-flash |

## Migration Phases

### Phase 1: Preparation and Setup

#### 1.1 Update Dependencies
**File**: `requirements.txt`

**Changes**:
- Add: `google-generativeai>=0.3.0`
- Remove: `openai` (after migration complete)
- Add: `google-auth>=2.23.0` (for authentication)

```bash
# New dependencies to add
google-generativeai>=0.3.0
google-auth>=2.23.0
```

#### 1.2 Update Environment Configuration
**File**: `env.example`

**Changes**:
```bash
# Remove OpenAI Configuration
# OPENAI_API_KEY=your-openai-api-key-here
# OPENAI_MODEL=gpt-4o
# OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Add Gemini Configuration
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_MODEL=gemini-1.5-pro
GEMINI_EMBEDDING_MODEL=text-embedding-004
GEMINI_PROJECT_ID=your-google-cloud-project-id
```

#### 1.3 Update Application Configuration
**File**: `app/configs/app_config.py`

**Changes**:
```python
# Remove OpenAI settings
# OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
# OPENAI_MODEL: str = Field(default="gpt-4o", env="OPENAI_MODEL")
# OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small", env="OPENAI_EMBEDDING_MODEL")

# Add Gemini settings
GEMINI_API_KEY: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
GEMINI_MODEL: str = Field(default="gemini-1.5-pro", env="GEMINI_MODEL")
GEMINI_EMBEDDING_MODEL: str = Field(default="text-embedding-004", env="GEMINI_EMBEDDING_MODEL")
GEMINI_PROJECT_ID: Optional[str] = Field(default=None, env="GEMINI_PROJECT_ID")
```

### Phase 2: Dependency Injection Update

#### 2.1 Update DI Container
**File**: `app/di/loader.py`

**Changes**:
```python
# Remove OpenAI client registration
# from openai import AsyncOpenAI
# container.register(
#     'openai_client',
#     lambda: AsyncOpenAI(api_key=settings.OPENAI_API_KEY),
#     singleton=True
# )

# Add Gemini client registration
import google.generativeai as genai
container.register(
    'gemini_client',
    lambda: _initialize_gemini_client(),
    singleton=True
)

def _initialize_gemini_client():
    """Initialize Gemini client with API key"""
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel(settings.GEMINI_MODEL)
```

### Phase 3: Service Layer Migration

#### 3.1 Update RAG Service
**File**: `app/services/ai/rag_service.py`

**Changes**:
- Replace OpenAI embeddings with Gemini embeddings
- Update embedding dimension handling (Gemini embeddings may have different dimensions)

```python
# Remove
# from openai import AsyncOpenAI

# Add
import google.generativeai as genai

class RAGService:
    def __init__(self, db: AsyncSession, gemini_client):
        self.db = db
        self.gemini_client = gemini_client

    async def retrieve(self, query: str, top_k: int = 5) -> str:
        # 1. Embed the query using Gemini
        embed_resp = genai.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            content=query,
            task_type="retrieval_document"
        )
        query_vector = embed_resp['embedding']
        # ... rest of the logic remains similar

    async def embed_text(self, text_input: str) -> list[float]:
        """Embed a single string using Gemini"""
        resp = genai.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            content=text_input,
            task_type="retrieval_document"
        )
        return resp['embedding']
```

**Important Note**: Gemini embeddings have different dimensions than OpenAI. You may need to:
- Re-index all existing knowledge chunks with new embeddings
- Update pgvector schema if dimensions differ
- OpenAI text-embedding-3-small: 1536 dimensions
- Gemini text-embedding-004: 768 dimensions

#### 3.2 Update Agent Service
**File**: `app/services/ai/agent_service.py`

**Changes**:
- Replace OpenAI chat completions with Gemini chat
- Update message format for Gemini API

```python
# Remove
# from openai import AsyncOpenAI

# Add
import google.generativeai as genai

class AgentService:
    @inject
    def __init__(
        self,
        rag = Provide["rag_service"],
        memory = Provide["memory_service"],
        prompt_builder = Provide["prompt_builder"],
        guardrails = Provide["guardrails_service"],
        gemini_client = Provide["gemini_client"],  # Changed from openai
    ):
        self.rag = rag
        self.memory = memory
        self.prompt_builder = prompt_builder
        self.guardrails = guardrails
        self.llm = gemini_client

    async def process_message(
        self,
        conversation_id: str,
        config: dict,
        message: str,
    ) -> tuple[str, float]:
        # ... existing code until LLM inference

        # 4. LLM inference with Gemini
        # Build conversation history for Gemini
        gemini_history = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg["content"]]})

        # Start chat with history
        chat = self.llm.start_chat(history=gemini_history)

        response = await chat.send_message_async(
            message,
            generation_config=genai.types.GenerationConfig(
                temperature=config.get("temperature", 0.7),
                max_output_tokens=config.get("max_tokens", 800),
            )
        )

        raw_response = response.text
        # ... rest of the logic remains similar
```

### Phase 4: Worker Migration

#### 4.1 Update AI Message Consumer
**File**: `app/workers/ai_message_consumer.py`

**Changes**:
- Replace OpenAI client instantiation with Gemini
- Update audio transcription (if uncommented)
- Update image description (if uncommented)

```python
# Remove
# from openai import AsyncOpenAI

# Add
import google.generativeai as genai

# In _process function, replace:
agent = AgentService(
    rag = RAGService(
        db = db_session,
        gemini_client = genai.GenerativeModel(settings.GEMINI_MODEL),
    ),
    memory = MemoryService(redis=..., window=settings.AI_MEMORY_WINDOW),
    prompt_builder = PromptBuilder(),
    guardrails = guardrails,
    gemini_client = genai.GenerativeModel(settings.GEMINI_MODEL),
)

# Update audio transcription (if enabled)
async def _transcribe_voice(audio_bytes: bytes) -> str:
    import io
    model = genai.GenerativeModel('gemini-1.5-pro')
    response = await model.generate_content_async(
        [
            {"mime_type": "audio/ogg", "data": audio_bytes},
            "Transcribe this audio"
        ]
    )
    return response.text

# Update image description (if enabled)
async def _describe_image(image_bytes: bytes, customer_text: str) -> str:
    import base64
    model = genai.GenerativeModel('gemini-1.5-pro')
    response = await model.generate_content_async(
        [
            {"mime_type": "image/jpeg", "data": image_bytes},
            customer_text or "What is in this image?"
        ]
    )
    return response.text
```

#### 4.2 Update Knowledge Consumer
**File**: `app/workers/knowledge_consumer.py`

**Changes**:
- Replace OpenAI embeddings with Gemini embeddings

```python
# Remove
# from openai import AsyncOpenAI

# Add
import google.generativeai as genai

# In _index function, replace:
# openai = container.resolve('openai_client')
gemini_client = container.resolve('gemini_client')

vectors = []
for chunk in chunks:
    embed_resp = genai.embed_content(
        model=settings.GEMINI_EMBEDDING_MODEL,
        content=chunk,
        task_type="retrieval_document"
    )
    vectors.append(embed_resp['embedding'])
```

### Phase 5: Database Migration

#### 5.1 Handle Embedding Dimension Change
**Critical Step**: Since Gemini embeddings have different dimensions (768 vs 1536), you must:

**Option A: Re-index all knowledge chunks**
```sql
-- Clear existing embeddings
TRUNCATE knowledge_chunks;

-- Re-run indexing for all documents
-- This will be handled by the knowledge_consumer when documents are re-processed
```

**Option B: Add new column for Gemini embeddings**
```sql
-- Add new column
ALTER TABLE knowledge_chunks ADD COLUMN embedding_gemini vector(768);

-- Create new index
CREATE INDEX ON knowledge_chunks USING ivfflat (embedding_gemini vector_cosine_ops);

-- Gradually migrate embeddings
```

**Recommendation**: Use Option A for cleaner migration, but requires re-processing all documents.

#### 5.2 Update RAG Service Query
**File**: `app/services/ai/rag_service.py`

If using Option B:
```python
sql = text("""
    SELECT content,
           1 - (embedding_gemini <=> :query_vec::vector) AS similarity
    FROM   knowledge_chunks
    WHERE  1 - (embedding_gemini <=> :query_vec::vector) > 0.72
    ORDER  BY embedding_gemini <=> :query_vec::vector
    LIMIT  :top_k
""")
```

### Phase 6: Testing Strategy

#### 6.1 Unit Tests
- Test RAGService with Gemini embeddings
- Test AgentService with Gemini chat
- Test embedding dimension compatibility
- Test message format conversion

#### 6.2 Integration Tests
- Test end-to-end message processing
- Test knowledge indexing with new embeddings
- Test audio transcription (if enabled)
- Test image description (if enabled)

#### 6.3 Performance Tests
- Compare response times between OpenAI and Gemini
- Test embedding generation speed
- Monitor token usage and costs

#### 6.4 Rollback Testing
- Ensure you can quickly revert to OpenAI if needed
- Test environment variable switching
- Verify database rollback procedures

### Phase 7: Deployment Strategy

#### 7.1 Staging Deployment
1. Deploy to staging environment first
2. Run full test suite
3. Test with sample conversations
4. Verify knowledge retrieval
5. Monitor for 24-48 hours

#### 7.2 Production Deployment - Blue-Green Approach
1. Deploy new version to production (but keep OpenAI as default)
2. Use feature flag to switch between OpenAI and Gemini
3. Gradually route traffic to Gemini (10% -> 50% -> 100%)
4. Monitor metrics and errors closely
5. Full cutover after validation

#### 7.3 Feature Flag Implementation
**File**: `app/configs/app_config.py`

```python
# Add feature flag
USE_GEMINI: bool = Field(default=False, env="USE_GEMINI")
```

**File**: `app/services/ai/agent_service.py`

```python
# In process_message, add conditional logic
if settings.USE_GEMINI:
    # Use Gemini client
else:
    # Use OpenAI client (for rollback)
```

### Phase 8: Post-Migration Tasks

#### 8.1 Monitoring
- Set up alerts for Gemini API errors
- Monitor response times
- Track token usage and costs
- Monitor embedding generation success rate

#### 8.2 Documentation Updates
- Update API documentation
- Update deployment guides
- Update troubleshooting guides
- Document Gemini-specific configurations

#### 8.3 Cleanup
- Remove OpenAI dependencies from requirements.txt
- Remove OpenAI code (after successful migration)
- Clean up unused environment variables
- Archive old OpenAI-related code

## Risk Assessment

### High Risks
1. **Embedding dimension mismatch** - Requires database migration
2. **API rate limits** - Gemini may have different rate limits
3. **Response quality differences** - May require prompt tuning
4. **Cost differences** - Monitor and compare costs

### Medium Risks
1. **Feature parity** - Some OpenAI features may not have direct Gemini equivalents
2. **Latency differences** - Gemini may have different latency characteristics
3. **Error handling** - Different error codes and messages

### Low Risks
1. **Configuration changes** - Straightforward environment variable updates
2. **Dependency updates** - Standard package management

## Rollback Plan

### Immediate Rollback (< 1 hour)
1. Set `USE_GEMINI=false` in environment
2. Restart services
3. Verify OpenAI is working

### Full Rollback (< 4 hours)
1. Revert code changes
2. Restore database to pre-migration state
3. Re-deploy previous version
4. Verify all functionality

## Timeline Estimate

| Phase | Duration |
|-------|----------|
| Phase 1: Preparation | 1-2 days |
| Phase 2: DI Update | 0.5 day |
| Phase 3: Service Migration | 2-3 days |
| Phase 4: Worker Migration | 1-2 days |
| Phase 5: Database Migration | 1-2 days |
| Phase 6: Testing | 3-5 days |
| Phase 7: Deployment | 2-3 days |
| Phase 8: Post-Migration | 1-2 days |
| **Total** | **11-19 days** |

## Success Criteria

1. All unit and integration tests pass
2. Response times are within acceptable limits (< 2x OpenAI)
3. Knowledge retrieval accuracy is maintained
4. No critical errors in production for 7 days
5. Cost is within budget (or acceptable increase)
6. Team is trained on Gemini-specific troubleshooting

## Additional Resources

- [Gemini API Documentation](https://ai.google.dev/docs)
- [Gemini Python SDK](https://github.com/google/generative-ai-python)
- [Migration Guide: OpenAI to Gemini](https://ai.google.dev/gemini-api/docs/migrate)
- [Gemini Pricing](https://ai.google.dev/pricing)

## Notes

- Gemini has a free tier with rate limits - suitable for testing
- Gemini 1.5 Flash is faster and cheaper than Pro for simple tasks
- Gemini supports larger context windows (up to 1M tokens for Pro)
- Consider using Gemini 1.5 Flash for high-volume, simple queries
- Consider using Gemini 1.5 Pro for complex reasoning tasks
