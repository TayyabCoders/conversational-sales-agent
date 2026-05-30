import httpx
from app.services.channels.base_channel import BaseChannel
from structlog import get_logger

logger = get_logger(__name__)


class WhatsAppChannel(BaseChannel):
    def __init__(self, api_version: str, app_secret: str):
        self.api_version = api_version
        self.base_url = f"https://graph.facebook.com/{api_version}"
        self.app_secret = app_secret

    async def send_message(
        self,
        recipient: str,
        message: str,
        phone_number_id: str = None,
        access_token: str = None,
        **kwargs,
    ) -> dict:
        try:
            logger.info(f"WhatsAppChannel: Sending message to {recipient}...")

            url = f"{self.base_url}/{phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "text",
                "text": {"body": message},
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                result = resp.json()

            logger.info(f"WhatsAppChannel: Message sent successfully to {recipient}")
            return result

        except Exception as e:
            logger.error(f"WhatsAppChannel: Failed to send message to {recipient}.", exc_info=True)
            raise e

    async def download_media(self, media_id: str, access_token: str = None, **kwargs) -> bytes:
        try:
            logger.info(f"WhatsAppChannel: Downloading media {media_id}...")

            # Step 1: Get media URL
            url_resp = await httpx.AsyncClient().get(
                f"{self.base_url}/{media_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            media_url = url_resp.json()["url"]

            # Step 2: Download actual file
            file_resp = await httpx.AsyncClient().get(
                media_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            content = file_resp.content

            logger.info(f"WhatsAppChannel: Media {media_id} downloaded successfully")
            return content

        except Exception as e:
            logger.error(f"WhatsAppChannel: Failed to download media {media_id}.", exc_info=True)
            raise e
