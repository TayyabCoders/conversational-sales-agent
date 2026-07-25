from fastapi import Request, BackgroundTasks, HTTPException
from fastapi.responses import PlainTextResponse
from dependency_injector.wiring import inject, Provide
from app.mediator.message_mediator import MessageMediator
from app.services.channels.adapters import get_webhook_adapter
from structlog import get_logger
from typing import Optional

logger = get_logger(__name__)


class WebhookController:
    @inject
    def __init__(
        self,
        message_mediator=Provide["message_mediator"],
        channel_repository=Provide["channel_repository"],
    ):
        self.mediator = message_mediator
        self.channel_repo = channel_repository

    async def handle_inbound(
        self,
        channel_type: str,
        request: Request,
        background_tasks: BackgroundTasks,
    ):
        try:
            logger.info("WebhookController: handling inbound message", channel_type=channel_type)

            channel = await self.channel_repo.get_active_by_type(channel_type)
            if not channel:
                raise HTTPException(404, f"No active channel of type {channel_type!r} registered")

            adapter = get_webhook_adapter(channel)
            body = await request.body()
            await adapter.verify_signature(body, dict(request.headers))

            data = await request.json()
            messages = await adapter.parse_messages(data)

            for message in messages:
                background_tasks.add_task(
                    self.mediator.handle_inbound,
                    message=message,
                    channel_id=channel.id,
                )

            logger.info("WebhookController: queued messages", channel_type=channel_type, count=len(messages))
            return {"status": "ok"}

        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            logger.error("WebhookController: failed to handle inbound", channel_type=channel_type, exc_info=True)
            raise

    async def verify_subscription(
        self,
        channel_type: str,
        mode: Optional[str],
        challenge: Optional[str],
        token: Optional[str],
    ):
        try:
            logger.info("WebhookController: verifying subscription", channel_type=channel_type)

            channel = await self.channel_repo.get_active_by_type(channel_type)
            if not channel:
                raise HTTPException(404, f"No active channel of type {channel_type!r} registered")

            adapter = get_webhook_adapter(channel)
            result = await adapter.verify_subscription(mode or "", challenge or "", token or "")

            if result is None:
                raise HTTPException(404, f"Channel type {channel_type!r} does not support hub verification")

            logger.info("WebhookController: subscription verified", channel_type=channel_type)
            return PlainTextResponse(result)

        except HTTPException:
            raise
        except Exception as e:
            logger.error("WebhookController: failed to verify subscription", channel_type=channel_type, exc_info=True)
            raise
