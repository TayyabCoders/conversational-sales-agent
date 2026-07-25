from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class ChannelCreate(BaseModel):
    type: str          # whatsapp | instagram | telegram | web
    name: str
    config: dict = {}  # {phone_number_id, access_token, app_secret, verify_token, ...}


class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None


class ChannelResponse(BaseModel):
    id: UUID
    type: str
    name: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
    # config is intentionally excluded from the response (contains credentials)
