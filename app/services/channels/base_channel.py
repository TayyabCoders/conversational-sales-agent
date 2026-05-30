from abc import ABC, abstractmethod
from structlog import get_logger

logger = get_logger(__name__)


class BaseChannel(ABC):
    @abstractmethod
    async def send_message(self, recipient: str, message: str, **kwargs) -> dict:
        """Send a text message to the recipient."""
        pass

    @abstractmethod
    async def download_media(self, media_id: str, **kwargs) -> bytes:
        """Download media (audio/image) by media ID."""
        pass
