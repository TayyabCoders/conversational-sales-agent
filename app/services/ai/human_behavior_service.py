import random
from structlog import get_logger

logger = get_logger(__name__)


def calculate_typing_delay(response_text: str) -> float:
    """
    Simulates human typing speed.
    Returns delay in seconds before sending the message.
    """
    try:
        CHARS_PER_SECOND = 8  # ~96 WPM average typing speed
        MIN_DELAY = 1.5  # Never respond instantly
        MAX_DELAY = 6.0  # Never keep waiting too long

        base = len(response_text) / CHARS_PER_SECOND
        jitter = random.uniform(-0.4, 1.0)
        delay = max(MIN_DELAY, min(MAX_DELAY, base + jitter))

        logger.debug(f"HumanBehaviorService: Calculated typing delay: {delay:.2f}s")
        return delay
    except Exception as e:
        logger.error("HumanBehaviorService: Failed to calculate typing delay.", exc_info=True)
        # Return default delay on error
        return 2.0
