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
    channel_id: UUID
    customer_identifier: str
    customer_name: Optional[str] = None
    status: str
    created_at: datetime
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    id: UUID
    channel_id: UUID
    customer_identifier: str
    customer_name: Optional[str] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TakeoverRequest(BaseModel):
    agent_id: UUID
