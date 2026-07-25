from typing import Any

from app.models.channel_model import Channel
from app.models.user_model import User
from app.models.conversation_model import Conversation
from app.models.message_model import Message
from app.models.lead_model import Lead
from app.models.knowledge_doc_model import KnowledgeDoc, KnowledgeChunk
from app.models.base_model import Base


async def initialize_models(database: Any) -> None:
    """Initialize database models by creating all tables.

    This uses the master engine from the Database wrapper to run
    SQLAlchemy's metadata.create_all synchronously within an async
    connection context.
    """
    # database is expected to be an instance of app.configs.database_config.Database
    engine = getattr(database, "master_engine", None)
    if engine is None:
        raise RuntimeError("Database master_engine is not initialized")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


__all__ = [
    "Channel",
    "User",
    "Conversation",
    "Message",
    "Lead",
    "KnowledgeDoc",
    "KnowledgeChunk",
    "initialize_models",
]
