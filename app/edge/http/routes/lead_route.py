from fastapi import APIRouter, Query, Depends
from typing import Optional
from dependency_injector.wiring import inject, Provide

from app.edge.http.controller.lead_controller import LeadController
from app.schemas.lead_schema import LeadStageUpdate, LeadResponse

router = APIRouter()


@router.get("/leads", response_model=list[LeadResponse])
@inject
async def list_leads(
    stage: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    controller: LeadController = Depends(Provide["lead_controller"]),
):
    return await controller.list_leads(stage, limit, offset)


@router.get("/leads/{lead_id}", response_model=LeadResponse)
@inject
async def get_lead(
    lead_id: str,
    controller: LeadController = Depends(Provide["lead_controller"]),
):
    return await controller.get_lead(lead_id)


@router.patch("/leads/{lead_id}/stage")
@inject
async def update_stage(
    lead_id: str,
    body: LeadStageUpdate,
    controller: LeadController = Depends(Provide["lead_controller"]),
):
    return await controller.update_stage(lead_id, body.stage)
