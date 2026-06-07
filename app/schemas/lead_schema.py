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
