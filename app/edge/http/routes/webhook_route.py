from fastapi import APIRouter, Request, BackgroundTasks, Query, Depends
from dependency_injector.wiring import inject, Provide

from app.edge.http.controller.webhook_controller import WebhookController

router = APIRouter()


@router.post("/webhooks/whatsapp")
@inject
async def receive_whatsapp(
    request: Request,
    background_tasks: BackgroundTasks,
    controller: WebhookController = Depends(Provide["webhook_controller"]),
):
    return await controller.handle_whatsapp(request, background_tasks)


@router.get("/webhooks/whatsapp")
@inject
async def verify_whatsapp(
    hub_mode: str = Query(alias="hub.mode"),
    hub_challenge: str = Query(alias="hub.challenge"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    controller: WebhookController = Depends(Provide["webhook_controller"]),
):
    return await controller.verify_whatsapp(hub_mode, hub_challenge, hub_verify_token)
