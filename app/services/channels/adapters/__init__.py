from app.services.channels.adapters.base_adapter import BaseWebhookAdapter
from app.services.channels.adapters.whatsapp_adapter import WhatsAppWebhookAdapter

# Maps channel.type → adapter class
WEBHOOK_ADAPTER_REGISTRY: dict[str, type[BaseWebhookAdapter]] = {
    "whatsapp": WhatsAppWebhookAdapter,
    "instagram": WhatsAppWebhookAdapter,  # Same Meta webhook format
}


def get_webhook_adapter(channel) -> BaseWebhookAdapter:
    """
    channel: Channel DB record.
    Returns an adapter initialised with that channel's config.
    """
    cls = WEBHOOK_ADAPTER_REGISTRY.get(channel.type)
    if cls is None:
        raise ValueError(
            f"No webhook adapter for channel type: {channel.type!r}. "
            f"Supported: {list(WEBHOOK_ADAPTER_REGISTRY)}"
        )
    return cls(channel=channel)


__all__ = [
    "BaseWebhookAdapter",
    "WhatsAppWebhookAdapter",
    "WEBHOOK_ADAPTER_REGISTRY",
    "get_webhook_adapter",
]
