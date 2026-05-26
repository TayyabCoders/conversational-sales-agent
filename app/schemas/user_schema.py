from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from uuid import UUID

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class User(UserBase):
    id: UUID
    role: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class PasswordResetToken(BaseModel):
    user_id: str
    token: str
    expires_at: datetime
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class RefreshToken(BaseModel):
    user_id: str
    token: str
    expires_at: datetime
    created_at: datetime
    is_revoked: bool = False
    
    model_config = ConfigDict(from_attributes=True)
