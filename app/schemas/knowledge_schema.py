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
