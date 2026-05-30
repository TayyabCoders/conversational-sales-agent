# AI Services Implementation — Step 6

This document outlines the implementation plan for AI services in the AI Sales Agent project, adapted to the current project structure with tenant logic excluded.

---

## Overview

This step implements the AI services required for intelligent conversation handling:
- **AgentService** — Main AI agent that coordinates RAG, memory, and LLM inference
- **RAGService** — Retrieval Augmented Generation using Qdrant and OpenAI embeddings
- **MemoryService** — Redis-based conversation history management
- **PromptBuilder** — Dynamic system prompt construction
- **GuardrailsService** — Safety validation and confidence scoring
- **HumanBehaviorService** — Typing delay simulation for human-like responses
- **LeadScorer** — Lead scoring based on conversation signals

**Note:** Tenant-specific parameters and logic are excluded from this implementation. Tenant logic will be implemented in a later phase.

---

## Current State Analysis

### Existing Services

#### `app/services/auth_service.py`
- Status: ✅ Exists
- Uses `@inject` decorator on `__init__`
- Uses `Provide["dependency_name"]` for dependency injection
- Uses structlog for logging
- Has try/except blocks with logging
- Returns data directly (not wrapped in response objects)

### Services to Create

#### `app/services/ai/agent_service.py`
- Status: ❌ Does not exist
- Needs: process_message method

#### `app/services/ai/rag_service.py`
- Status: ❌ Does not exist
- Needs: retrieve method

#### `app/services/ai/memory_service.py`
- Status: ❌ Does not exist
- Needs: get_history, append, clear methods

#### `app/services/ai/prompt_builder.py`
- Status: ❌ Does not exist
- Needs: build method

#### `app/services/ai/guardrails_service.py`
- Status: ❌ Does not exist
- Needs: validate, check_escalation_trigger methods

#### `app/services/ai/human_behavior_service.py`
- Status: ❌ Does not exist
- Needs: calculate_typing_delay function

#### `app/services/ai/lead_scorer.py`
- Status: ❌ Does not exist
- Needs: update_from_message method

---

## Implementation Details

### 1. Create `app/services/ai/agent_service.py`

Create new file with agent service:

```python
from app.di.container import container
from dependency_injector.wiring import inject, Provide
from openai import AsyncOpenAI
from app.services.ai.rag_service import RAGService
from app.services.ai.memory_service import MemoryService
from app.services.ai.prompt_builder import PromptBuilder
from app.services.ai.guardrails_service import GuardrailsService
from structlog import get_logger

logger = get_logger(__name__)


class AgentService:
    @inject
    def __init__(
        self,
        rag = Provide["rag_service"],
        memory = Provide["memory_service"],
        prompt_builder = Provide["prompt_builder"],
        guardrails = Provide["guardrails_service"],
        openai = Provide["openai_client"],
    ):
        self.rag = rag
        self.memory = memory
        self.prompt_builder = prompt_builder
        self.guardrails = guardrails
        self.llm = openai

    async def process_message(
        self,
        conversation_id: str,
        config: dict,
        message: str,
    ) -> tuple[str, float]:
        """Returns (response_text, confidence_score)"""
        try:
            logger.info(f"AgentService: Processing message for conversation {conversation_id}...")

            # 1. Load conversation history from Redis
            history = await self.memory.get_history(conversation_id)

            # 2. Retrieve relevant knowledge from Qdrant
            knowledge = await self.rag.retrieve(
                query=message,
                top_k=5,
            )

            # 3. Build system prompt dynamically
            system_prompt = self.prompt_builder.build(
                persona_name=config.get("persona_name", "Assistant"),
                business_name=config.get("business_name", ""),
                tone=config.get("tone", "friendly and professional"),
                knowledge_context=knowledge,
                hard_rules=config.get("hard_rules", []),
            )

            # 4. LLM inference
            response = await self.llm.chat.completions.create(
                model=config.get("model", "gpt-4o"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    *history,
                    {"role": "user", "content": message},
                ],
                temperature=config.get("temperature", 0.7),
                max_tokens=config.get("max_tokens", 800),
            )

            raw_response = response.choices[0].message.content

            # 5. Run guardrails (safety + confidence check)
            safe_response, confidence = await self.guardrails.validate(
                response=raw_response,
                config=config,
            )

            # 6. Save response to memory
            await self.memory.append(conversation_id, "assistant", safe_response)

            logger.info(f"AgentService: AI response generated for conversation {conversation_id}", extra={
                "tokens_used": response.usage.total_tokens,
                "confidence": confidence,
            })

            return safe_response, confidence

        except Exception as e:
            logger.error(f"AgentService: Failed to process message for conversation {conversation_id}.", exc_info=True)
            raise e
```

**Changes from build plan:**
- Removed `tenant_id` parameter from `process_message` method (tenant logic excluded)
- Renamed `tenant_config` to `config` (tenant logic excluded)
- Removed `tenant_id` from `rag.retrieve` call
- Added `@inject` decorator on `__init__` following project pattern
- Added try/except blocks with logging following project pattern
- Changed from `logging` to `structlog`

---

### 2. Create `app/services/ai/rag_service.py`

Create new file with RAG service:

```python
from app.di.container import container
from dependency_injector.wiring import inject, Provide
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from openai import AsyncOpenAI
from structlog import get_logger

logger = get_logger(__name__)


class RAGService:
    @inject
    def __init__(
        self,
        qdrant = Provide["qdrant_client"],
        openai = Provide["openai_client"],
    ):
        self.qdrant = qdrant
        self.openai = openai
        self.collection = "knowledge_chunks"

    async def retrieve(self, query: str, top_k: int = 5) -> str:
        try:
            logger.info("RAGService: Retrieving knowledge...")

            # 1. Embed the query
            embed_resp = await self.openai.embeddings.create(
                model="text-embedding-3-small",
                input=query,
            )
            query_vector = embed_resp.data[0].embedding

            # 2. Search Qdrant — no tenant filter (tenant logic excluded)
            results = await self.qdrant.search(
                collection_name=self.collection,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=0.72,
            )

            if not results:
                logger.info("RAGService: No relevant knowledge found.")
                return "No relevant knowledge found for this query."

            # 3. Format as numbered context
            chunks = [f"[{i+1}] {r.payload['content']}" for i, r in enumerate(results)]
            context = "\n\n".join(chunks)

            logger.info(f"RAGService: Retrieved {len(chunks)} knowledge chunks.")
            return context

        except Exception as e:
            logger.error("RAGService: Failed to retrieve knowledge.", exc_info=True)
            raise e
```

**Changes from build plan:**
- Removed `tenant_id` parameter from `retrieve` method (tenant logic excluded)
- Removed `collection` parameter (hardcoded in __init__)
- Removed tenant filter from Qdrant search (tenant logic excluded)
- Added `@inject` decorator on `__init__` following project pattern
- Added try/except blocks with logging following project pattern
- Changed from `logging` to `structlog`

---

### 3. Create `app/services/ai/memory_service.py`

Create new file with memory service:

```python
from app.di.container import container
from dependency_injector.wiring import inject, Provide
import json
from redis.asyncio import Redis
from structlog import get_logger

logger = get_logger(__name__)


class MemoryService:
    @inject
    def __init__(self, redis = Provide["redis_client"]):
        self.redis = redis
        self.window = 20
        self.ttl = 7200  # 2 hours

    def _key(self, conversation_id: str) -> str:
        return f"conv:memory:{conversation_id}"

    async def get_history(self, conversation_id: str) -> list[dict]:
        try:
            raw = await self.redis.get(self._key(conversation_id))
            return json.loads(raw) if raw else []
        except Exception as e:
            logger.error(f"MemoryService: Failed to get history for conversation {conversation_id}.", exc_info=True)
            return []

    async def append(self, conversation_id: str, role: str, content: str) -> None:
        try:
            history = await self.get_history(conversation_id)
            history.append({"role": role, "content": content})
            # Keep only last N messages (sliding window)
            history = history[-self.window:]
            await self.redis.setex(
                self._key(conversation_id), self.ttl, json.dumps(history)
            )
        except Exception as e:
            logger.error(f"MemoryService: Failed to append to history for conversation {conversation_id}.", exc_info=True)
            raise e

    async def clear(self, conversation_id: str) -> None:
        try:
            await self.redis.delete(self._key(conversation_id))
        except Exception as e:
            logger.error(f"MemoryService: Failed to clear history for conversation {conversation_id}.", exc_info=True)
            raise e
```

**Changes from build plan:**
- Added `@inject` decorator on `__init__` following project pattern
- Added try/except blocks with logging following project pattern
- Changed from `logging` to `structlog`

---

### 4. Create `app/services/ai/prompt_builder.py`

Create new file with prompt builder:

```python
from structlog import get_logger

logger = get_logger(__name__)


class PromptBuilder:
    def build(
        self,
        persona_name: str,
        business_name: str,
        tone: str,
        knowledge_context: str,
        hard_rules: list[str],
    ) -> str:
        try:
            rules_text = "\n".join(f"- {r}" for r in hard_rules) if hard_rules else "None"

            prompt = f"""You are {persona_name}, a sales representative at {business_name}.
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

            logger.debug("PromptBuilder: System prompt built successfully.")
            return prompt

        except Exception as e:
            logger.error("PromptBuilder: Failed to build system prompt.", exc_info=True)
            raise e
```

**Changes from build plan:**
- Added try/except blocks with logging following project pattern
- Changed from `logging` to `structlog`

---

### 5. Create `app/services/ai/guardrails_service.py`

Create new file with guardrails service:

```python
from structlog import get_logger

logger = get_logger(__name__)

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
        config: dict,
    ) -> tuple[str, float]:
        """Returns (safe_response, confidence_score 0.0–1.0)"""
        try:
            logger.info("GuardrailsService: Validating response...")

            # Confidence heuristic — uncertainty phrases lower score
            text_lower = response.lower()
            hits = sum(1 for phrase in UNCERTAINTY_PHRASES if phrase in text_lower)
            confidence = max(0.3, 1.0 - (hits * 0.2))

            # Block competitor mentions if configured
            blocked_words = config.get("blocked_words", [])
            for word in blocked_words:
                response = response.replace(word, "[REDACTED]")

            logger.info(f"GuardrailsService: Response validated with confidence {confidence}.")
            return response, confidence

        except Exception as e:
            logger.error("GuardrailsService: Failed to validate response.", exc_info=True)
            raise e

    def check_escalation_trigger(self, customer_message: str) -> bool:
        """Returns True if customer is explicitly asking for a human."""
        try:
            msg_lower = customer_message.lower()
            result = any(kw in msg_lower for kw in ESCALATION_KEYWORDS)
            logger.info(f"GuardrailsService: Escalation trigger check: {result}")
            return result
        except Exception as e:
            logger.error("GuardrailsService: Failed to check escalation trigger.", exc_info=True)
            raise e
```

**Changes from build plan:**
- Renamed `tenant_config` to `config` (tenant logic excluded)
- Added try/except blocks with logging following project pattern
- Changed from `logging` to `structlog`

---

### 6. Create `app/services/ai/human_behavior_service.py`

Create new file with human behavior service:

```python
import random
from structlog import get_logger

logger = get_logger(__name__)


def calculate_typing_delay(response_text: str) -> float:
    """
    Simulates human typing speed.
    Returns delay in seconds before sending the message.
    """
    try:
        CHARS_PER_SECOND = 8  # ~96 WPM average typing speed
        MIN_DELAY = 1.5  # Never respond instantly
        MAX_DELAY = 6.0  # Never keep waiting too long

        base = len(response_text) / CHARS_PER_SECOND
        jitter = random.uniform(-0.4, 1.0)
        delay = max(MIN_DELAY, min(MAX_DELAY, base + jitter))

        logger.debug(f"HumanBehaviorService: Calculated typing delay: {delay:.2f}s")
        return delay
    except Exception as e:
        logger.error("HumanBehaviorService: Failed to calculate typing delay.", exc_info=True)
        # Return default delay on error
        return 2.0
```

**Changes from build plan:**
- Added try/except blocks with logging following project pattern
- Changed from `logging` to `structlog`
- Added default delay on error

---

### 7. Create `app/services/ai/lead_scorer.py`

Create new file with lead scorer:

```python
from app.di.container import container
from dependency_injector.wiring import inject, Provide
from app.repositories.lead_repository import LeadRepository
from structlog import get_logger

logger = get_logger(__name__)

SIGNAL_SCORES = {
    "asks_pricing": 20,
    "asks_availability": 25,
    "mentions_budget": 20,
    "asks_to_book": 30,
    "name_provided": 10,
    "just_browsing": -15,
}

STAGE_MAP = [
    (86, "qualified"),
    (61, "hot"),
    (31, "warm"),
    (0, "cold"),
]


class LeadScorer:
    @inject
    def __init__(self, lead_repo = Provide["lead_repository"]):
        self.repo = lead_repo

    async def update_from_message(
        self,
        lead_id: str,
        message: str,
    ) -> None:
        try:
            logger.info(f"LeadScorer: Updating lead {lead_id} from message...")

            lead = await self.repo.get_by_id(lead_id)
            if not lead:
                logger.warning(f"LeadScorer: Lead {lead_id} not found.")
                return

            # Detect signals in message
            text_lower = message.lower()
            signals = []

            if "price" in text_lower or "cost" in text_lower or "how much" in text_lower:
                signals.append("asks_pricing")
            if "available" in text_lower or "when" in text_lower:
                signals.append("asks_availability")
            if "budget" in text_lower or "can afford" in text_lower:
                signals.append("mentions_budget")
            if "book" in text_lower or "schedule" in text_lower or "reserve" in text_lower:
                signals.append("asks_to_book")
            if "just looking" in text_lower or "just browsing" in text_lower:
                signals.append("just_browsing")

            # Calculate new score
            score_change = sum(SIGNAL_SCORES.get(signal, 0) for signal in signals)
            new_score = max(0, min(100, lead.score + score_change))

            # Determine stage based on score
            new_stage = "cold"
            for threshold, stage in STAGE_MAP:
                if new_score >= threshold:
                    new_stage = stage
                    break

            # Update lead
            await self.repo.update(lead_id, {"score": new_score, "stage": new_stage})

            logger.info(f"LeadScorer: Lead {lead_id} updated - score: {new_score}, stage: {new_stage}")

        except Exception as e:
            logger.error(f"LeadScorer: Failed to update lead {lead_id}.", exc_info=True)
            raise e
```

**Changes from build plan:**
- Added `@inject` decorator on `__init__` following project pattern
- Added try/except blocks with logging following project pattern
- Changed from `logging` to `structlog`
- Implemented signal detection logic (was incomplete in build plan)

---

### 8. Update `app/services/ai/__init__.py`

Add imports for the new services (if file exists, otherwise create it):

```python
from app.services.ai.agent_service import AgentService
from app.services.ai.rag_service import RAGService
from app.services.ai.memory_service import MemoryService
from app.services.ai.prompt_builder import PromptBuilder
from app.services.ai.guardrails_service import GuardrailsService
from app.services.ai.human_behavior_service import calculate_typing_delay
from app.services.ai.lead_scorer import LeadScorer

__all__ = [
    "AgentService",
    "RAGService",
    "MemoryService",
    "PromptBuilder",
    "GuardrailsService",
    "calculate_typing_delay",
    "LeadScorer",
]
```

**Note:** Check if `__init__.py` exists in the ai directory. If not, create it with the above content.

---

### 9. Update `app/services/__init__.py`

Add imports for the ai services (if file exists):

```python
from app.services.auth_service import AuthService
from app.services.ai import *

__all__ = [
    "AuthService",
    # AI services (imported with *)
]
```

---

## Implementation Checklist

- [ ] Create `app/services/ai/agent_service.py`
  - [ ] Create process_message method
  - [ ] Remove tenant_id parameters
  - [ ] Add proper imports and logging
- [ ] Create `app/services/ai/rag_service.py`
  - [ ] Create retrieve method
  - [ ] Remove tenant_id parameter
  - [ ] Add proper imports and logging
- [ ] Create `app/services/ai/memory_service.py`
  - [ ] Create get_history method
  - [ ] Create append method
  - [ ] Create clear method
  - [ ] Add proper imports and logging
- [ ] Create `app/services/ai/prompt_builder.py`
  - [ ] Create build method
  - [ ] Add proper imports and logging
- [ ] Create `app/services/ai/guardrails_service.py`
  - [ ] Create validate method
  - [ ] Create check_escalation_trigger method
  - [ ] Remove tenant_config parameter
  - [ ] Add proper imports and logging
- [ ] Create `app/services/ai/human_behavior_service.py`
  - [ ] Create calculate_typing_delay function
  - [ ] Add proper imports and logging
- [ ] Create `app/services/ai/lead_scorer.py`
  - [ ] Create update_from_message method
  - [ ] Add proper imports and logging
- [ ] Update/Create `app/services/ai/__init__.py`
  - [ ] Add imports for new services
  - [ ] Update `__all__` list
- [ ] Update `app/services/__init__.py`
  - [ ] Add imports for ai services

---

## Notes

- **Tenant logic excluded** — All `tenant_id` and `tenant_config` parameters have been removed from service methods. Tenant logic will be implemented in a later phase.
- **Project structure preserved** — All services follow the existing pattern of using `@inject` decorator on `__init__`, `Provide["xxx"]` for dependency injection, structlog for logging, and try/except blocks with logging.
- **RAG changes** — Qdrant search no longer includes tenant filter since tenant logic is excluded.
- **Configuration** — Services use a generic `config` dict instead of `tenant_config` since tenant logic is excluded.
- **External dependencies** — Services depend on external clients (OpenAI, Qdrant, Redis) which will need to be configured in the DI container.
- **Lead scorer implementation** — Implemented signal detection logic that was incomplete in the build plan.
