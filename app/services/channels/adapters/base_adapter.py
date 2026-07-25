from abc import ABC, abstractmethod
from app.schemas.webhook_schema import InboundMessage


class BaseWebhookAdapter(ABC):
    @abstractmethod
    async def verify_signature(self, body: bytes, headers: dict) -> None: ...

    @abstractmethod
    async def parse_messages(self, data: dict) -> list[InboundMessage]: ...

    async def verify_subscription(self, mode: str, challenge: str, token: str) -> str | None:
        """Return the challenge string to echo back, or None if not supported by this channel."""
        return None
