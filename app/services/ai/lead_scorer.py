from app.di.container import container
from dependency_injector.wiring import inject, Provide
from app.repositories.lead_repository import LeadRepository
from structlog import get_logger

logger = get_logger(__name__)

SIGNAL_SCORES = {
    # Generic sales signals
    "asks_pricing": 20,
    "asks_availability": 25,
    "mentions_budget": 20,
    "asks_to_book": 30,
    "name_provided": 10,
    "just_browsing": -15,
    # Travel-specific signals
    "mentions_destination": 15,
    "provides_dates": 20,
    "mentions_travelers": 15,
    "asks_packages": 25,
    "asks_flights": 20,
    "asks_hotels": 20,
    "mentions_visa": 15,
    "asks_itinerary": 20,
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

            # Generic sales signals
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

            # Travel-specific signals
            if any(dest in text_lower for dest in ["paris", "dubai", "london", "new york", "tokyo", "bali", "thailand", "maldives", "turkey", "europe", "asia", "usa", "canada", "australia"]):
                signals.append("mentions_destination")
            if any(date_word in text_lower for date_word in ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december", "week", "month", "date"]):
                signals.append("provides_dates")
            if "family" in text_lower or "couple" in text_lower or "group" in text_lower or "people" in text_lower or "travelers" in text_lower:
                signals.append("mentions_travelers")
            if "package" in text_lower or "deal" in text_lower or "offer" in text_lower:
                signals.append("asks_packages")
            if "flight" in text_lower or "air" in text_lower or "fly" in text_lower:
                signals.append("asks_flights")
            if "hotel" in text_lower or "resort" in text_lower or "stay" in text_lower or "accommodation" in text_lower:
                signals.append("asks_hotels")
            if "visa" in text_lower or "passport" in text_lower:
                signals.append("mentions_visa")
            if "itinerary" in text_lower or "plan" in text_lower or "schedule" in text_lower:
                signals.append("asks_itinerary")

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
