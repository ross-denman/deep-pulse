import logging
from typing import Dict

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """
    Physical budget safety limit for the Deep Pulse Swarm.
    Prevents empty successful endpoint (HTTP 200 but garbage extraction)
    from endlessly draining the $2.00 compute budget.
    """

    def __init__(self, failure_threshold: int = 3):
        self.threshold = failure_threshold
        # Tracks sequential empty extractions per distinct perimeter/target
        self._target_failures: Dict[str, int] = {}
        
    def check_state(self, target_url: str) -> bool:
        """
        Returns True if the circuit is TRIPPED (unsafe to proceed).
        Returns False if the circuit is CLOSED (safe to proceed).
        """
        failures = self._target_failures.get(target_url, 0)
        is_tripped = failures >= self.threshold
        if is_tripped:
            logger.critical(f"[CIRCUIT BREAKER TRIPPED] Target {target_url} exceeded {self.threshold} garbage extraction failures. Halting execution to protect compute budget.")
        return is_tripped

    def record_pulse(self, target_url: str, confidence_score: float, is_schema_drift: bool = False):
        """
        Records the successful HTTP extraction evaluation.
        If confidence is extremely low (e.g. < 0.2) and it's not detected as Semantic Drift, 
        it implies the API returned 200 OK but hallucinated the data payload.
        """
        if is_schema_drift:
            # Schema drift is handled by the Immune System natively, not a raw garbage error.
            self.reset(target_url)
            return

        # If data is terrible but connection succeeded, increment failure.
        if confidence_score < 0.2:
            current_failures = self._target_failures.get(target_url, 0)
            self._target_failures[target_url] = current_failures + 1
            logger.warning(f"Circuit Breaker Warning: Low confidence payload from {target_url}. (Strike {self._target_failures[target_url]}/{self.threshold})")
        else:
            self.reset(target_url)

    def reset(self, target_url: str):
        """Resets the breaker for a specific target upon a verified high-signal extraction."""
        if target_url in self._target_failures:
            self._target_failures[target_url] = 0
