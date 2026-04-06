import logging
from typing import List

logger = logging.getLogger(__name__)

class CuriosityBot:
    """
    Maintains hypothesis state across deep discovery nodes.
    Features a loop breaker to ensure Diversity Heuristics when hitting 404/dead ends.
    """
    
    def __init__(self, memory_manager, perimeter: str):
        self.memory = memory_manager
        self.perimeter = perimeter
        self.hunch_state = {}
        
        # Diversity cascade for fallback when an initial hypothesis loops
        self.diversity_heuristics = [
            "archive",
            "sitemap.xml",
            "data",
            "reports",
            "research"
        ]

    def _get_hunch_category(self, hunch: str) -> str:
        """Determines what category/pattern the hunch is enforcing."""
        for h in self.diversity_heuristics:
            if h in hunch.lower():
                return h
        return "unknown"

    def record_failure(self, hunch: str):
        """Logs a failure for a specific hypothesis category."""
        category = self._get_hunch_category(hunch)
        if category == "unknown":
            return
            
        if category not in self.hunch_state:
            self.hunch_state[category] = 0
            
        self.hunch_state[category] += 1
        logger.debug(f"CuriosityBot: Logged failure for '{category}' (Count: {self.hunch_state[category]})")

    async def generate_hunch(self, raw_content: str, episode_id: int) -> str:
        """
        Generates a new hypothesis/hunch.
        Implements the Loop Breaker.
        """
        # Determine current active heuristic based on failure counts
        active_heuristic = None
        for h in self.diversity_heuristics:
            failures = self.hunch_state.get(h, 0)
            if failures < 3:
                active_heuristic = h
                break
                
        if not active_heuristic:
            logger.warning("CuriosityBot: All diversity heuristics exhausted!")
            active_heuristic = "archive" # Last resort fallback
            
        # Log if we broke a loop
        for h, count in self.hunch_state.items():
            if count >= 3 and h != active_heuristic:
                logger.warning(f"CuriosityBot LOOP BREAKER ACTIVATED: '{h}' failed {count} times. Pivoting RLM to '{active_heuristic}'.")
                # Reset down to 3 so we don't spam the warning
                self.hunch_state[h] = 3

        hunch = f"Hunch: The pulse might be buried in the '{self.perimeter}_{active_heuristic}' based on nav clues."
        
        # Log to RLM Memory
        self.memory.log_hunch(episode_id, hunch)
        return hunch
