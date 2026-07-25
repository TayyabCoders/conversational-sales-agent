# Channel Abstraction — Implementation Guide

> **Goal:** Store channel configuration in a proper `channels` DB table. Remove all WhatsApp-specific hardcoding so any channel (WhatsApp, Instagram, Telegram, web) flows through the same pipeline. Credentials come from the DB, not env vars.

---

## Architecture

```
Inbound  POST /webhooks/{channel_type}          e.g. /webhooks/whatsapp
                 │
                 ▼
    WebhookController.handle_inbound(channel_type)
                 │
                 ▼
    channel_repo.get_active_by_type("whatsapp")   ← DB lookup → Channel record
                 │
                 ▼
    get_webhook_adapter(channel_record)            ← type-based dispatch
       │  verify_signature(body, headers)          ← uses channel.config["app_secret"]
       └─ parse_messages(data) → [InboundMessage]
                 │
                 ▼
    MessageMediator.handle_inbound(message, channel_id=UUID)
       stores Conversation (channel_id FK), saves Message, publishes to RabbitMQ
                 │
    RabbitMQ payload: {conversation_id, lead_id, message_text, channel_id}
                 │
                 ▼
    ai_message_consumer
       │  channel_repo.get_by_id(channel_id)       ← DB lookup
       └─ build_channel_client(channel_record)      ← type-based factory
                 │
                 ▼
    channel_client.send_message(recipient=sender_id, message=response_text)
```

---

## DB Schema

### channels table (new)

```sql
CREATE TABLE channels (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type        VARCHAR(50) NOT NULL,   -- whatsapp | instagram | telegram | web
    name        VARCHAR(200) NOT NULL,  -- "Main WhatsApp", "Support Bot"
    config      JSONB NOT NULL DEFAULT '{}',
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);
```

**config JSONB keys by channel type:**

| type | keys |
|------|------|
| whatsapp / instagram | `phone_number_id`, `access_token`, `app_secret`, `verify_token`, `api_version` |
| telegram | `bot_token` |
| web | `api_key` |

### conversations table (changed)

```sql
-- BEFORE
channel VARCHAR(50)

-- AFTER
channel_id UUID NOT NULL REFERENCES channels(id)
```

---

## New Files

| File | Purpose |
|------|---------|
| [app/models/channel_model.py](../../app/models/channel_model.py) | SQLAlchemy `Channel` model |
| [app/repositories/channel_repository.py](../../app/repositories/channel_repository.py) | `get_active_by_type()`, `list_active()` |
| [app/schemas/channel_schema.py](../../app/schemas/channel_schema.py) | `ChannelCreate`, `ChannelUpdate`, `ChannelResponse` |
| [app/schemas/channels/whatsapp_schema.py](../../app/schemas/channels/whatsapp_schema.py) | WhatsApp-specific Pydantic models (moved from webhook_schema) |
| [app/services/channels/adapters/base_adapter.py](../../app/services/channels/adapters/base_adapter.py) | `BaseWebhookAdapter` abstract class |
| [app/services/channels/adapters/whatsapp_adapter.py](../../app/services/channels/adapters/whatsapp_adapter.py) | Meta webhook parse + HMAC verify (reads from channel.config) |
| [alembic/versions/add_channels_table.py](../../alembic/versions/add_channels_table.py) | Migration: create channels table, add channel_id FK, seed default WA channel |

---

## Changed Files

| File | Change |
|------|--------|
| `app/models/conversation_model.py` | `channel: str` → `channel_id: UUID FK channels.id` |
| `app/schemas/webhook_schema.py` | Trimmed to `InboundMessage` only; `from_number` → `sender_id` |
| `app/schemas/conversation_schema.py` | `channel: str` → `channel_id: UUID`; `customer_phone` → `customer_identifier` |
| `app/schemas/lead_schema.py` | `customer_phone` → `customer_identifier` |
| `app/configs/app_config.py` | Added `WHATSAPP_VERIFY_TOKEN` to Settings |
| `app/utils/security_util.py` | `verify_whatsapp_signature` → `verify_meta_signature(body, sig, secret)` |
| `app/services/channels/__init__.py` | `build_channel_client(channel_record)` factory (reads config from DB row) |
| `app/services/channels/whatsapp_channel.py` | Stores `phone_number_id`/`access_token` in `__init__`; falls back to env vars |
| `app/services/channels/adapters/__init__.py` | `get_webhook_adapter(channel_record)` — adapter initialised with channel config |
| `app/edge/http/routes/webhook_route.py` | `/webhooks/{channel_type}` parameterised |
| `app/edge/http/controller/webhook_controller.py` | DB lookup by type; dispatches adapter; passes `channel_id` UUID to mediator |
| `app/edge/http/controller/conversation_controller.py` | Resolves `?channel=whatsapp` → `channel_id` UUID via ChannelRepository |
| `app/mediator/message_mediator.py` | `channel: str` → `channel_id: UUID`; `from_number` → `sender_id` |
| `app/mediator/conversation_mediator.py` | `channel: str` → `channel_id` |
| `app/services/conversation_service.py` | `channel: str` → `channel_id` |
| `app/repositories/conversation_repository.py` | `channel` → `channel_id`; `customer_phone` → `customer_identifier` |
| `app/repositories/lead_repository.py` | `customer_phone` → `customer_identifier` |
| `app/workers/ai_message_consumer.py` | Reads `channel_id` from payload; fetches Channel from DB; `build_channel_client(channel_record)` |
| `app/models/lead_model.py` | `customer_phone` → `customer_identifier` |

---

## Migrations to Run

Two migrations, in order:

```bash
alembic upgrade head
```

This runs both:
1. `channel_001` — renames `customer_phone` → `customer_identifier` in conversations + leads
2. `channel_002` — creates `channels` table, seeds a default WhatsApp channel, adds `channel_id` FK to conversations, drops the old `channel` string column

---

## After Deployment — Set Credentials

The migration seeds a default WhatsApp channel with empty config (`{}`). You need to update it with your real credentials. Currently you can do this directly in the DB or via a management script:

```sql
UPDATE channels
SET config = '{
    "phone_number_id": "your_phone_number_id",
    "access_token": "your_access_token",
    "app_secret": "your_meta_app_secret",
    "verify_token": "your_verify_token",
    "api_version": "v21.0"
}'::jsonb
WHERE type = 'whatsapp';
```

The `build_channel_client()` and `WhatsAppWebhookAdapter` both fall back to env var values if `config` is empty, so existing env-var setup continues to work without running the SQL above.

---

## Adding a New Channel

Four steps, zero changes to existing files:

### 1. Channel send implementation
```python
# app/services/channels/telegram_channel.py
class TelegramChannel(BaseChannel):
    def __init__(self, bot_token: str):
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    async def send_message(self, recipient: str, message: str, **kwargs) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/sendMessage", json={
                "chat_id": recipient,
                "text": message,
            })
            resp.raise_for_status()
            return resp.json()

    async def download_media(self, media_id: str, **kwargs) -> bytes:
        ...
```

### 2. Webhook adapter
```python
# app/services/channels/adapters/telegram_adapter.py
class TelegramWebhookAdapter(BaseWebhookAdapter):
    def __init__(self, channel=None):
        self._channel = channel

    async def verify_signature(self, body: bytes, headers: dict) -> None:
        pass  # implement secret_token check if needed

    async def parse_messages(self, data: dict) -> list[InboundMessage]:
        msg = data.get("message", {})
        if not msg:
            return []
        return [InboundMessage(
            sender_id=str(msg["from"]["id"]),
            message_id=str(msg["message_id"]),
            text=msg.get("text"),
        )]
```

### 3. Register in both registries
```python
# app/services/channels/__init__.py — add to build_channel_client
if channel.type == "telegram":
    return TelegramChannel(bot_token=cfg.get("bot_token", ""))

# app/services/channels/adapters/__init__.py — add to WEBHOOK_ADAPTER_REGISTRY
"telegram": TelegramWebhookAdapter,
```

### 4. Create channel record in DB
```sql
INSERT INTO channels (type, name, config, is_active)
VALUES ('telegram', 'Support Bot', '{"bot_token": "..."}', true);
```

Then register the webhook with Telegram once:
```
POST https://api.telegram.org/bot{TOKEN}/setWebhook
body: {"url": "https://your-domain.com/webhooks/telegram"}
```

---

## API — Query Conversations by Channel

The `GET /conversations` endpoint still accepts `?channel=whatsapp`. The controller resolves the type slug to a `channel_id` UUID internally — the API surface stays the same.

---

## Deployment Checklist

- [ ] Run `alembic upgrade head` (runs both `channel_001` and `channel_002`)
- [ ] Verify the default WhatsApp channel was seeded: `SELECT * FROM channels;`
- [ ] Update channel config with real credentials (SQL above, or via future admin API)
- [ ] Test WhatsApp flow end-to-end: send message → conversation created → AI reply received
- [ ] Meta webhook URL unchanged: `POST /webhooks/whatsapp` still works
