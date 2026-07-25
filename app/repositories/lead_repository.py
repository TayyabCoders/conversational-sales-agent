from typing import Optional
from app.repositories.base_repository import BaseRepository
from app.models.lead_model import Lead
from app.di.container import container
from dependency_injector.wiring import inject, Provide
from structlog import get_logger
from typing import Any

logger = get_logger(__name__)


class LeadRepository(BaseRepository[Lead]):
    @inject
    def __init__(self, database = Provide["database"], cache: Optional[Any] = Provide["cache"]):
        super().__init__(Lead, database, cache)

    async def get_or_create(
        self,
        conversation_id: str,
        customer_identifier: str,
    ) -> Lead:
        try:
            logger.info("LeadRepository: Getting or creating lead...")

            # Check if lead already exists for this conversation
            existing = await self.findOne(filters={"conversation_id": conversation_id})
            if existing:
                logger.info(f"LeadRepository: Found existing lead {existing.id}")
                return existing

            # Create new lead
            lead_data = {
                "conversation_id": conversation_id,
                "customer_identifier": customer_identifier,
                "score": 0,
                "stage": "cold",
            }
            lead = await self.create(lead_data)

            logger.info(f"LeadRepository: Created new lead {lead.id}")
            return lead

        except Exception as e:
            logger.error("LeadRepository: Failed to get or create lead.", exc_info=True)
            raise e

    async def update_stage(self, lead_id: str, stage: str) -> None:
        try:
            logger.info(f"LeadRepository: Updating stage for lead {lead_id}...")

            await self.update(lead_id, {"stage": stage})

            logger.info(f"LeadRepository: Updated stage for lead {lead_id}")

        except Exception as e:
            logger.error(f"LeadRepository: Failed to update stage for lead {lead_id}.", exc_info=True)
            raise e

    async def list_all(
        self,
        stage: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Lead]:
        try:
            logger.info("LeadRepository: Listing leads...")

            filters = {}
            if stage:
                filters["stage"] = stage

            leads = await self.findAll(filters=filters)
            
            # Apply pagination manually
            result = leads[offset:offset + limit]

            logger.info(f"LeadRepository: Listed {len(result)} leads")
            return result

        except Exception as e:
            logger.error("LeadRepository: Failed to list leads.", exc_info=True)
            raise e
