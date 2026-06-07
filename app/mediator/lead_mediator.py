from app.di.container import container
from dependency_injector.wiring import inject, Provide
from structlog import get_logger

logger = get_logger(__name__)


class LeadMediator:
    @inject
    def __init__(
        self,
        lead_service = Provide["lead_service"]
    ):
        self.lead_service = lead_service

    async def list_leads(
        self,
        stage: str = None,
        limit: int = 50,
        offset: int = 0,
    ):
        try:
            logger.info("LeadMediator: Listing leads...")
            
            result = await self.lead_service.list_leads(
                stage=stage,
                limit=limit,
                offset=offset,
            )
            
            logger.info("LeadMediator: Leads listed successfully.")
            
            return result
        
        except Exception as e:
            logger.error("LeadMediator: Failed to list leads.", exc_info=True)
            raise e

    async def get_lead(self, lead_id: str):
        try:
            logger.info(f"LeadMediator: Getting lead {lead_id}...")
            
            result = await self.lead_service.get_lead(lead_id)
            
            logger.info(f"LeadMediator: Lead {lead_id} retrieved successfully.")
            
            return result
        
        except Exception as e:
            logger.error(f"LeadMediator: Failed to get lead {lead_id}.", exc_info=True)
            raise e

    async def update_lead_stage(self, lead_id: str, stage: str):
        try:
            logger.info(f"LeadMediator: Updating lead {lead_id} stage to {stage}...")
            
            result = await self.lead_service.update_lead_stage(lead_id, stage)
            
            logger.info(f"LeadMediator: Lead {lead_id} stage updated successfully.")
            
            return result
        
        except Exception as e:
            logger.error(f"LeadMediator: Failed to update lead {lead_id} stage.", exc_info=True)
            raise e
