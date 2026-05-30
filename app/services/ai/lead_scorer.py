from app.di.container import container
from dependency_injector.wiring import inject, Provide
from app.repositories.lead_repository import LeadRepository
from structlog import get_logger

logger = get_logger(__name__)

SIGNAL_SCORES = {
    "asks_pricing": 20,
    "asks_availability": 25,
    "mentions_budget": 20,
    "asks_to_book": 30,
    "name_provided": 10,
    "just_browsing": -15,
}

STAGE_MAP = [
    (86, "qualified"),
    (61, "hot"),
    (31, "warm"),
    (0, "cold"),
]


class LeadScorer:
    @inject
    def __init__(self, lead_repo = Provide["lead_repository"]):
        self.repo = lead_repo

    async def update_from_message(
        self,
        lead_id: str,
        message: str,
    ) -> None:
        try:
            logger.info(f"LeadScorer: Updating lead {lead_id} from message...")

            lead = await self.repo.get_by_id(lead_id)
            if not lead:
                logger.warning(f"LeadScorer: Lead {lead_id} not found.")
                return

            # Detect signals in message
            text_lower = message.lower()
            signals = []

            if "price" in text_lower or "cost" in text_lower or "how much" in text_lower:
                signals.append("asks_pricing")
            if "available" in text_lower or "when" in text_lower:
                signals.append("asks_availability")
            if "budget" in text_lower or "can afford" in text_lower:
                signals.append("mentions_budget")
            if "book" in text_lower or "schedule" in text_lower or "reserve" in text_lower:
                signals.append("asks_to_book")
            if "just looking" in text_lower or "just browsing" in text_lower:
                signals.append("just_browsing")

            # Calculate new score
            score_change = sum(SIGNAL_SCORES.get(signal, 0) for signal in signals)
            new_score = max(0, min(100, lead.score + score_change))

            # Determine stage based on score
            new_stage = "cold"
            for threshold, stage in STAGE_MAP:
                if new_score >= threshold:
                    new_stage = stage
                    break

            # Update lead
            await self.repo.update(lead_id, {"score": new_score, "stage": new_stage})

            logger.info(f"LeadScorer: Lead {lead_id} updated - score: {new_score}, stage: {new_stage}")

        except Exception as e:
            logger.error(f"LeadScorer: Failed to update lead {lead_id}.", exc_info=True)
            raise e
