# Routes Implementation — Step 3

This document outlines the implementation plan for FastAPI routes in the AI Sales Agent project, adapted to the current project structure with tenant logic excluded.

---

## Overview

This step implements the FastAPI routes required for API endpoints:
- **Webhook Route** — WhatsApp webhook endpoints for receiving and verifying webhooks
- **Conversation Route** — Conversation management endpoints
- **Knowledge Route** — Knowledge base document management endpoints
- **Lead Route** — Lead management endpoints

**Note:** Tenant-specific parameters and logic are excluded from this implementation. Tenant logic will be implemented in a later phase.

---

## Current State Analysis

### Existing Routes

#### `app/edge/http/routes/auth_route.py`
- Status: ✅ Exists
- Contains: Authentication-related endpoints

#### `app/edge/http/routes/example_auth_routes.py`
- Status: ✅ Exists
- Contains: Example authentication routes

#### `app/edge/http/routes/health_route.py`
- Status: ✅ Exists
- Contains: Health check endpoints

#### `app/edge/http/routes/users_route.py`
- Status: ✅ Exists
- Contains: User management endpoints

### Routes to Create

#### `app/edge/http/routes/webhook_route.py`
- Status: ❌ Does not exist
- Needs: POST /webhooks/whatsapp (receive webhook), GET /webhooks/whatsapp (verify webhook)

#### `app/edge/http/routes/conversation_route.py`
- Status: ❌ Does not exist
- Needs: GET /conversations, GET /conversations/{id}, POST /conversations/{id}/takeover, POST /conversations/{id}/release

#### `app/edge/http/routes/knowledge_route.py`
- Status: ❌ Does not exist
- Needs: POST /knowledge/upload, GET /knowledge/docs, DELETE /knowledge/docs/{id}, POST /knowledge/docs/{id}/reindex

#### `app/edge/http/routes/lead_route.py`
- Status: ❌ Does not exist
- Needs: GET /leads, GET /leads/{id}, PATCH /leads/{id}/stage

---

## Implementation Details

### 1. Create `app/edge/http/routes/webhook_route.py`

Create new file with WhatsApp webhook endpoints:

```python
from fastapi import APIRouter, Request, BackgroundTasks, Query
from app.di.container import Container
from dependency_injector.wiring import inject, Provide

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/whatsapp")
@inject
async def receive_whatsapp(
    request: Request,
    background_tasks: BackgroundTasks,
    controller=Provide[Container.webhook_controller],
):
    return await controller.handle_whatsapp(request, background_tasks)


@router.get("/whatsapp")
@inject
async def verify_whatsapp(
    hub_mode: str = Query(alias="hub.mode"),
    hub_challenge: str = Query(alias="hub.challenge"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    controller=Provide[Container.webhook_controller],
):
    return await controller.verify_whatsapp(hub_mode, hub_challenge, hub_verify_token)
```

**Changes from build plan:**
- Removed `tenant_id` parameter from both endpoints (tenant logic excluded)
- Removed `/whatsapp/{tenant_id}` path, simplified to `/whatsapp`

---

### 2. Create `app/edge/http/routes/conversation_route.py`

Create new file with conversation management endpoints:

```python
from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.di.container import Container
from dependency_injector.wiring import inject, Provide
from app.schemas.conversation_schema import TakeoverRequest

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("/")
@inject
async def list_conversations(
    status: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    controller=Provide[Container.conversation_controller],
):
    return await controller.list_conversations(status, channel, limit, offset)


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

**Changes from build plan:**
- Removed `tenant_id` parameter from `list_conversations` endpoint (tenant logic excluded)

---

### 3. Create `app/edge/http/routes/knowledge_route.py`

Create new file with knowledge base management endpoints:

```python
from fastapi import APIRouter, UploadFile, File
from app.di.container import Container
from dependency_injector.wiring import inject, Provide

router = APIRouter(prefix="/knowledge", tags=["Knowledge"])


@router.post("/upload")
@inject
async def upload_document(
    file: UploadFile = File(...),
    controller=Provide[Container.knowledge_controller],
):
    return await controller.upload(file)


@router.get("/docs")
@inject
async def list_docs(
    controller=Provide[Container.knowledge_controller],
):
    return await controller.list_docs()


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

**Changes from build plan:**
- Removed `tenant_id` parameter from `upload_document` and `list_docs` endpoints (tenant logic excluded)

---

### 4. Create `app/edge/http/routes/lead_route.py`

Create new file with lead management endpoints:

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
    stage: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    controller=Provide[Container.lead_controller],
):
    return await controller.list_leads(stage, limit, offset)


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

**Changes from build plan:**
- Removed `tenant_id` parameter from `list_leads` endpoint (tenant logic excluded)

---

### 5. Update `app/edge/http/routes/__init__.py`

Add imports for the new routes (if file exists, otherwise create it):

```python
from app.edge.http.routes.webhook_route import router as webhook_router
from app.edge.http.routes.conversation_route import router as conversation_router
from app.edge.http.routes.knowledge_route import router as knowledge_router
from app.edge.http.routes.lead_route import router as lead_router

__all__ = [
    "webhook_router",
    "conversation_router",
    "knowledge_router",
    "lead_router",
]
```

**Note:** Check if `__init__.py` exists in the routes directory. If not, create it with the above content.

---

## Implementation Checklist

- [ ] Create `app/edge/http/routes/webhook_route.py`
  - [ ] Create POST /webhooks/whatsapp endpoint
  - [ ] Create GET /webhooks/whatsapp endpoint
- [ ] Create `app/edge/http/routes/conversation_route.py`
  - [ ] Create GET /conversations endpoint
  - [ ] Create GET /conversations/{id} endpoint
  - [ ] Create POST /conversations/{id}/takeover endpoint
  - [ ] Create POST /conversations/{id}/release endpoint
- [ ] Create `app/edge/http/routes/knowledge_route.py`
  - [ ] Create POST /knowledge/upload endpoint
  - [ ] Create GET /knowledge/docs endpoint
  - [ ] Create DELETE /knowledge/docs/{id} endpoint
  - [ ] Create POST /knowledge/docs/{id}/reindex endpoint
- [ ] Create `app/edge/http/routes/lead_route.py`
  - [ ] Create GET /leads endpoint
  - [ ] Create GET /leads/{id} endpoint
  - [ ] Create PATCH /leads/{id}/stage endpoint
- [ ] Update/Create `app/edge/http/routes/__init__.py`
  - [ ] Add imports for new routers
  - [ ] Update `__all__` list

---

## Notes

- **Tenant logic excluded** — All `tenant_id` parameters have been removed from route signatures. Tenant logic will be implemented in a later phase.
- **Project structure preserved** — All routes follow the existing pattern of using FastAPI APIRouter with dependency_injector's `@inject` decorator and `Provide[Container.xxx]`.
- **Controller dependencies** — These routes expect controllers to be registered in the DI container. The controllers themselves will be implemented in Step 4.
- **Webhook verification** — The webhook verification endpoint will need a verify token. Since tenant logic is excluded, this may need to be configured via environment variables or a default value.
