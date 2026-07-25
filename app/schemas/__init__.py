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
from app.schemas.webhook_schema import InboundMessage
from app.schemas.channels.whatsapp_schema import (
    WhatsAppTextMessage,
    WhatsAppAudio,
    WhatsAppImage,
    WhatsAppMessage,
    WhatsAppContact,
    WhatsAppValue,
    WhatsAppChange,
    WhatsAppEntry,
    WhatsAppWebhookPayload,
)
from app.schemas.channel_schema import ChannelCreate, ChannelUpdate, ChannelResponse
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
    # Channel schemas
    "ChannelCreate",
    "ChannelUpdate",
    "ChannelResponse",
    # Knowledge schemas
    "KnowledgeDocResponse",
    # Lead schemas
    "LeadResponse",
    "LeadStageUpdate",
]
