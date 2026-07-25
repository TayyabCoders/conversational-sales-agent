from fastapi import APIRouter, Depends
from dependency_injector.wiring import inject, Provide
from uuid import UUID

from app.edge.http.controller.channel_controller import ChannelController
from app.schemas.channel_schema import ChannelCreate, ChannelUpdate, ChannelResponse

router = APIRouter()


@router.get("/channels", response_model=list[ChannelResponse])
@inject
async def list_channels(
    controller: ChannelController = Depends(Provide["channel_controller"]),
):
    return await controller.list_channels()


@router.post("/channels", response_model=ChannelResponse, status_code=201)
@inject
async def create_channel(
    body: ChannelCreate,
    controller: ChannelController = Depends(Provide["channel_controller"]),
):
    return await controller.create_channel(body)


@router.get("/channels/{channel_id}", response_model=ChannelResponse)
@inject
async def get_channel(
    channel_id: UUID,
    controller: ChannelController = Depends(Provide["channel_controller"]),
):
    return await controller.get_channel(str(channel_id))


@router.patch("/channels/{channel_id}", response_model=ChannelResponse)
@inject
async def update_channel(
    channel_id: UUID,
    body: ChannelUpdate,
    controller: ChannelController = Depends(Provide["channel_controller"]),
):
    return await controller.update_channel(str(channel_id), body)


@router.delete("/channels/{channel_id}")
@inject
async def delete_channel(
    channel_id: UUID,
    controller: ChannelController = Depends(Provide["channel_controller"]),
):
    return await controller.delete_channel(str(channel_id))
