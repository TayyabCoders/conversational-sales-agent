from app.di.container import container
from dependency_injector.wiring import inject, Provide
from structlog import get_logger

logger = get_logger(__name__)


class LeadController:
    @inject
    def __init__(self, lead_mediator = Provide["lead_mediator"]):
        self.lead_mediator = lead_mediator

    async def list_leads(self, stage, limit, offset):
        try:
            logger.info("LeadController: Listing leads...")

            result = await self.lead_mediator.list_leads(
                stage=stage, limit=limit, offset=offset
            )

            logger.info("LeadController: Leads listed successfully.")
            return result

        except Exception as e:
            logger.error("LeadController: Failed to list leads.", exc_info=True)
            raise e

    async def get_lead(self, lead_id: str):
        try:
            logger.info(f"LeadController: Getting lead {lead_id}...")

            result = await self.lead_mediator.get_lead(lead_id)

            logger.info(f"LeadController: Lead {lead_id} retrieved successfully.")
            return result

        except Exception as e:
            logger.error(f"LeadController: Failed to get lead {lead_id}.", exc_info=True)
            raise e

    async def update_stage(self, lead_id: str, stage: str):
        try:
            logger.info(f"LeadController: Updating lead {lead_id} stage to {stage}...")

            result = await self.lead_mediator.update_lead_stage(lead_id, stage)

            logger.info(f"LeadController: Lead {lead_id} stage updated to {stage} successfully.")
            return result

        except Exception as e:
            logger.error(f"LeadController: Failed to update lead {lead_id} stage.", exc_info=True)
            raise e
