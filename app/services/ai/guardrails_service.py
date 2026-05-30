from structlog import get_logger

logger = get_logger(__name__)

ESCALATION_KEYWORDS = [
    "talk to a person", "human agent", "real person",
    "speak to someone", "manager please", "connect me to staff",
]

UNCERTAINTY_PHRASES = [
    "i think", "i believe", "probably", "maybe",
    "i am not sure", "i cannot find", "i don't know",
]


class GuardrailsService:
    async def validate(
        self,
        response: str,
        config: dict,
    ) -> tuple[str, float]:
        """Returns (safe_response, confidence_score 0.0–1.0)"""
        try:
            logger.info("GuardrailsService: Validating response...")

            # Confidence heuristic — uncertainty phrases lower score
            text_lower = response.lower()
            hits = sum(1 for phrase in UNCERTAINTY_PHRASES if phrase in text_lower)
            confidence = max(0.3, 1.0 - (hits * 0.2))

            # Block competitor mentions if configured
            blocked_words = config.get("blocked_words", [])
            for word in blocked_words:
                response = response.replace(word, "[REDACTED]")

            logger.info(f"GuardrailsService: Response validated with confidence {confidence}.")
            return response, confidence

        except Exception as e:
            logger.error("GuardrailsService: Failed to validate response.", exc_info=True)
            raise e

    def check_escalation_trigger(self, customer_message: str) -> bool:
        """Returns True if customer is explicitly asking for a human."""
        try:
            msg_lower = customer_message.lower()
            result = any(kw in msg_lower for kw in ESCALATION_KEYWORDS)
            logger.info(f"GuardrailsService: Escalation trigger check: {result}")
            return result
        except Exception as e:
            logger.error("GuardrailsService: Failed to check escalation trigger.", exc_info=True)
            raise e
