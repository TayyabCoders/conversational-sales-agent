from fastapi import APIRouter, Request, BackgroundTasks, Query, Depends
from dependency_injector.wiring import inject, Provide
from typing import Optional

from app.edge.http.controller.webhook_controller import WebhookController

router = APIRouter()


@router.post("/webhooks/{channel}")
@inject
async def receive_webhook(
    channel: str,
    request: Request,
    background_tasks: BackgroundTasks,
    controller: WebhookController = Depends(Provide["webhook_controller"]),
):
    return await controller.handle_inbound(channel, request, background_tasks)


@router.get("/webhooks/{channel}")
@inject
async def verify_webhook(
    channel: str,
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    controller: WebhookController = Depends(Provide["webhook_controller"]),
):
    return await controller.verify_subscription(channel, hub_mode, hub_challenge, hub_verify_token)
