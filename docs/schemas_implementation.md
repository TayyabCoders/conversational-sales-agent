# Schemas Implementation — Step 2

This document outlines the implementation plan for Pydantic schemas in the AI Sales Agent project, adapted to the current project structure with tenant logic excluded.

---

## Overview

This step implements the Pydantic schemas required for data validation and serialization:
- **Webhook Schema** — WhatsApp Cloud API payload structures
- **Conversation Schema** — Conversation and message response models
- **Knowledge Schema** — Knowledge base document response models
- **Lead Schema** — Lead response and update models

**Note:** Tenant schema and tenant-specific logic are deferred to a later phase.

---

## Current State Analysis

### Existing Schemas

#### `app/schemas/auth_schema.py`
- Status: ✅ Exists
- Contains: LoginRequest, TokenResponse, TokenData, RefreshTokenRequest, etc.
- Uses Pydantic v2 with modern type hints

#### `app/schemas/user_schema.py`
- Status: ✅ Exists
- Contains: UserBase, UserCreate, UserUpdate, User, etc.
- Uses `model_config = ConfigDict(from_attributes=True)` pattern

#### `app/schemas/socket_schema.py`
- Status: ✅ Exists
- Contains: WebSocket-related schemas

### Schemas to Create

#### `app/schemas/webhook_schema.py`
- Status: ❌ Does not exist
- Needs: WhatsApp webhook payload schemas and normalized inbound message

#### `app/schemas/conversation_schema.py`
- Status: ❌ Does not exist
- Needs: MessageResponse, ConversationResponse, ConversationListResponse, TakeoverRequest

#### `app/schemas/knowledge_schema.py`
- Status: ❌ Does not exist
- Needs: KnowledgeDocResponse

#### `app/schemas/lead_schema.py`
- Status: ❌ Does not exist
- Needs: LeadResponse, LeadStageUpdate

---

## Implementation Details

### 1. Create `app/schemas/webhook_schema.py`

Create new file with WhatsApp webhook schemas:

```python
from pydantic import BaseModel, Field
from typing import Optional, List


# ── WhatsApp Cloud API payload structure ──────────────────────────

class WhatsAppTextMessage(BaseModel):
    body: str


class WhatsAppAudio(BaseModel):
    id: str
    mime_type: Optional[str] = None


class WhatsAppImage(BaseModel):
    id: str
    mime_type: Optional[str] = None


class WhatsAppMessage(BaseModel):
    id: str
    from_: str = Field(alias="from")
    timestamp: str
    type: str  # text | audio | image | document
    text: Optional[WhatsAppTextMessage] = None
    audio: Optional[WhatsAppAudio] = None
    image: Optional[WhatsAppImage] = None


class WhatsAppContact(BaseModel):
    profile: Optional[dict] = None
    wa_id: Optional[str] = None


class WhatsAppValue(BaseModel):
    messaging_product: str
    metadata: Optional[dict] = None
    messages: Optional[List[WhatsAppMessage]] = None
    contacts: Optional[List[WhatsAppContact]] = None


class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: str


class WhatsAppEntry(BaseModel):
    id: str
    changes: List[WhatsAppChange]


class WhatsAppWebhookPayload(BaseModel):
    object: str
    entry: List[WhatsAppEntry]


# ── Normalised inbound message (channel-agnostic) ────────────────

class InboundMessage(BaseModel):
    from_number: str
    message_id: str
    text: Optional[str] = None
    media_type: Optional[str] = None  # audio | image | document
    media_id: Optional[str] = None  # Meta media ID to download
    contact_name: Optional[str] = None
```

**New file** with WhatsApp webhook payload structures and normalized inbound message schema.

---

### 2. Create `app/schemas/conversation_schema.py`

Create new file with conversation and message response schemas:

```python
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    media_type: Optional[str] = None
    media_url: Optional[str] = None
    tokens_used: Optional[int] = None
    latency_ms: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    id: UUID
    channel: str
    customer_phone: str
    customer_name: Optional[str] = None
    status: str
    created_at: datetime
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    id: UUID
    channel: str
    customer_phone: str
    customer_name: Optional[str] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TakeoverRequest(BaseModel):
    agent_id: UUID
```

**New file** with conversation and message response schemas. Note: Added `media_url` field to MessageResponse to match the updated model.

---

### 3. Create `app/schemas/knowledge_schema.py`

Create new file with knowledge document response schema:

```python
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class KnowledgeDocResponse(BaseModel):
    id: UUID
    filename: str
    file_type: str
    status: str
    chunk_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

**New file** with knowledge document response schema.

---

### 4. Create `app/schemas/lead_schema.py`

Create new file with lead response and update schemas:

```python
from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class LeadResponse(BaseModel):
    id: UUID
    customer_phone: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    score: int
    stage: str
    qualification_data: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeadStageUpdate(BaseModel):
    stage: str  # cold | warm | hot | qualified | converted
```

**New file** with lead response and stage update schemas.

---

### 5. Update `app/schemas/__init__.py`

Add imports for the new schemas (if file exists, otherwise create it):

```python
from app.schemas.auth_schema import (
    LoginRequest,
    TokenResponse,
    TokenData,
    RefreshTokenRequest,
    RefreshTokenResponse,
    LogoutRequest,
    RequestPasswordResetRequest,
    RequestPasswordResetResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from app.schemas.user_schema import (
    UserBase,
    UserCreate,
    UserUpdate,
    User,
    PasswordResetToken,
    RefreshToken as UserRefreshToken,
)
from app.schemas.socket_schema import *
from app.schemas.webhook_schema import (
    WhatsAppTextMessage,
    WhatsAppAudio,
    WhatsAppImage,
    WhatsAppMessage,
    WhatsAppContact,
    WhatsAppValue,
    WhatsAppChange,
    WhatsAppEntry,
    WhatsAppWebhookPayload,
    InboundMessage,
)
from app.schemas.conversation_schema import (
    MessageResponse,
    ConversationResponse,
    ConversationListResponse,
    TakeoverRequest,
)
from app.schemas.knowledge_schema import KnowledgeDocResponse
from app.schemas.lead_schema import LeadResponse, LeadStageUpdate


__all__ = [
    # Auth schemas
    "LoginRequest",
    "TokenResponse",
    "TokenData",
    "RefreshTokenRequest",
    "RefreshTokenResponse",
    "LogoutRequest",
    "RequestPasswordResetRequest",
    "RequestPasswordResetResponse",
    "ResetPasswordRequest",
    "ResetPasswordResponse",
    # User schemas
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "User",
    "PasswordResetToken",
    "UserRefreshToken",
    # Socket schemas (imported with *)
    # Webhook schemas
    "WhatsAppTextMessage",
    "WhatsAppAudio",
    "WhatsAppImage",
    "WhatsAppMessage",
    "WhatsAppContact",
    "WhatsAppValue",
    "WhatsAppChange",
    "WhatsAppEntry",
    "WhatsAppWebhookPayload",
    "InboundMessage",
    # Conversation schemas
    "MessageResponse",
    "ConversationResponse",
    "ConversationListResponse",
    "TakeoverRequest",
    # Knowledge schemas
    "KnowledgeDocResponse",
    # Lead schemas
    "LeadResponse",
    "LeadStageUpdate",
]
```

**Note:** Check if `__init__.py` exists in the schemas directory. If not, create it with the above content.

---

## Implementation Checklist

- [ ] Create `app/schemas/webhook_schema.py`
  - [ ] Create WhatsApp webhook payload schemas
  - [ ] Create InboundMessage schema
- [ ] Create `app/schemas/conversation_schema.py`
  - [ ] Create MessageResponse schema (with media_url)
  - [ ] Create ConversationResponse schema
  - [ ] Create ConversationListResponse schema
  - [ ] Create TakeoverRequest schema
- [ ] Create `app/schemas/knowledge_schema.py`
  - [ ] Create KnowledgeDocResponse schema
- [ ] Create `app/schemas/lead_schema.py`
  - [ ] Create LeadResponse schema
  - [ ] Create LeadStageUpdate schema
- [ ] Update/Create `app/schemas/__init__.py`
  - [ ] Add imports for new schemas
  - [ ] Update `__all__` list

---

## Notes

- **Tenant logic excluded** — All tenant-related schemas have been excluded from this implementation. Tenant logic will be implemented in a later phase.
- **Project structure preserved** — All schemas follow the existing pattern of using `BaseModel` with `model_config = ConfigDict(from_attributes=True)` and modern Python type hints.
- **MessageResponse enhancement** — Added `media_url` field to MessageResponse to match the updated Message model.
- **Field alias** — WhatsAppMessage uses `Field(alias="from")` for the `from_` field to handle the reserved keyword in the WhatsApp API payload.
