from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class SocketEvent(BaseModel):
    """Base model for all WebSocket events"""
    type: str = Field(..., description="Type of the event (e.g., chat, subscribe, broadcast)")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event data")

class ChatMessage(BaseModel):
    target_id: str
    content: str

class SubscribeMessage(BaseModel):
    room_id: str

class BroadcastMessage(BaseModel):
    content: str

class SocketResponse(BaseModel):
    """Standardized response format for WebSocket messages"""
    type: str
    data: Any
    status: str = "success"
    message: Optional[str] = None
