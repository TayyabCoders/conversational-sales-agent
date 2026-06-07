from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from structlog import get_logger
from dependency_injector.wiring import inject, Provide

logger = get_logger(__name__)


class LeadService:
    @inject
    def __init__(
        self,
        lead_repository = Provide["lead_repository"],
        prometheus = Provide["prometheus"],
    ):
        self.lead_repository = lead_repository
        self.prometheus = prometheus

    async def list_leads(
        self,
        stage: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        try:
            logger.info("LeadService: Listing leads...")
            
            leads = await self.lead_repository.list_all(
                stage=stage,
                limit=limit,
                offset=offset,
            )
            
            logger.info(f"LeadService: Listed {len(leads)} leads")
            
            # Record business event
            self.prometheus.record_business_event("lead_list", "success")
            
            return {"data": leads, "total": len(leads)}
        
        except Exception as e:
            logger.error("LeadService: Failed to list leads.", exc_info=True)
            raise e

    async def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        try:
            logger.info(f"LeadService: Getting lead {lead_id}...")
            
            lead = await self.lead_repository.get_by_id(lead_id)
            
            if not lead:
                logger.warning(f"LeadService: Lead {lead_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Lead not found"
                )
            
            logger.info(f"LeadService: Retrieved lead {lead_id}")
            
            # Record business event
            self.prometheus.record_business_event("lead_get", "success")
            
            return lead
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"LeadService: Failed to get lead {lead_id}.", exc_info=True)
            raise e

    async def update_lead_stage(self, lead_id: str, stage: str) -> Dict[str, Any]:
        try:
            logger.info(f"LeadService: Updating lead {lead_id} stage to {stage}...")
            
            valid_stages = {"cold", "warm", "hot", "qualified", "converted"}
            if stage not in valid_stages:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid stage. Choose from: {valid_stages}"
                )
            
            await self.lead_repository.update_stage(lead_id, stage)
            
            logger.info(f"LeadService: Lead {lead_id} stage updated to {stage}")
            
            # Record business event
            self.prometheus.record_business_event("lead_stage_update", "success")
            
            return {"message": f"Lead stage updated to {stage}"}
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"LeadService: Failed to update lead {lead_id} stage.", exc_info=True)
            raise e
