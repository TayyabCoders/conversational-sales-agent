from app.configs.app_config import settings
from app.services.channels.base_channel import BaseChannel
from app.services.channels.whatsapp_channel import WhatsAppChannel


def build_channel_client(channel) -> BaseChannel:
    """
    Build a fully-configured BaseChannel from a Channel DB record.
    Credentials come from channel.config; falls back to env vars for easy local dev.
    """
    cfg = channel.config or {}

    if channel.type in ("whatsapp", "instagram"):
        return WhatsAppChannel(
            api_version=cfg.get("api_version") or settings.WHATSAPP_API_VERSION,
            app_secret=cfg.get("app_secret") or settings.META_APP_SECRET or "",
            phone_number_id=cfg.get("phone_number_id") or settings.WHATSAPP_PHONE_NUMBER_ID,
            access_token=cfg.get("access_token") or settings.WHATSAPP_ACCESS_TOKEN,
        )

    raise ValueError(
        f"Unsupported channel type: {channel.type!r}. "
        f"Supported types: whatsapp, instagram"
    )


__all__ = ["BaseChannel", "WhatsAppChannel", "build_channel_client"]
