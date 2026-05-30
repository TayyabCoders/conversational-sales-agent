from app.repositories.lead_repository import LeadRepository
from fastapi import HTTPException
from structlog import get_logger

logger = get_logger(__name__)


class LeadController:
    @inject
    def __init__(self, lead_repo = Provide["lead_repository"]):
        self.repo = lead_repo

    async def list_leads(self, stage, limit, offset):
        try:
            logger.info("LeadController: Listing leads...")

            leads = await self.repo.list_all(stage=stage, limit=limit, offset=offset)

            logger.info("LeadController: Leads listed successfully.")
            return {"data": leads, "total": len(leads)}

        except Exception as e:
            logger.error("LeadController: Failed to list leads.", exc_info=True)
            raise e

    async def get_lead(self, lead_id: str):
        try:
            logger.info(f"LeadController: Getting lead {lead_id}...")

            lead = await self.repo.get_by_id(lead_id)
            if not lead:
                raise HTTPException(404, "Lead not found")

            logger.info(f"LeadController: Lead {lead_id} retrieved successfully.")
            return lead

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"LeadController: Failed to get lead {lead_id}.", exc_info=True)
            raise e

    async def update_stage(self, lead_id: str, stage: str):
        try:
            logger.info(f"LeadController: Updating lead {lead_id} stage to {stage}...")

            valid_stages = {"cold", "warm", "hot", "qualified", "converted"}
            if stage not in valid_stages:
                raise HTTPException(400, f"Invalid stage. Choose from: {valid_stages}")

            await self.repo.update_stage(lead_id, stage)

            logger.info(f"LeadController: Lead {lead_id} stage updated to {stage} successfully.")
            return {"message": f"Lead stage updated to {stage}"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"LeadController: Failed to update lead {lead_id} stage.", exc_info=True)
            raise e
