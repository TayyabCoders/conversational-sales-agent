from fastapi import APIRouter, Depends, Query
from typing import Optional
from dependency_injector.wiring import inject, Provide

from app.edge.http.controller.conversation_controller import ConversationController
from app.schemas.conversation_schema import TakeoverRequest, ConversationResponse, ConversationListResponse

router = APIRouter()


@router.get("/conversations", response_model=list[ConversationListResponse])
@inject
async def list_conversations(
    status: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    controller: ConversationController = Depends(Provide["conversation_controller"]),
):
    return await controller.list_conversations(status, channel, limit, offset)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
@inject
async def get_conversation(
    conversation_id: str,
    controller: ConversationController = Depends(Provide["conversation_controller"]),
):
    return await controller.get_conversation(conversation_id)


@router.post("/conversations/{conversation_id}/takeover")
@inject
async def takeover(
    conversation_id: str,
    body: TakeoverRequest,
    controller: ConversationController = Depends(Provide["conversation_controller"]),
):
    return await controller.takeover(conversation_id, str(body.agent_id))


@router.post("/conversations/{conversation_id}/release")
@inject
async def release(
    conversation_id: str,
    controller: ConversationController = Depends(Provide["conversation_controller"]),
):
    return await controller.release(conversation_id)
