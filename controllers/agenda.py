import json
import logging
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any

from src.public.storage.queue import MasterOutpostQueue
from src.public.core.models import InterestProfile

# Setup logging
logger = logging.getLogger("agenda_controller")

class AgendaController:
    """
    Translates the Sovereign Interest Profile into actionable mesh inquiries.
    Ensures the Nexus investigative agenda is always seeded with user-defined targets.
    """
    def __init__(self, 
                 profile_path: str = "harvest/user_profile.json",
                 db_path: Path = None):
        self.profile_path = Path(profile_path)
        self.queue = MasterOutpostQueue(db_path) if db_path else MasterOutpostQueue()

    def load_profile(self) -> InterestProfile:
        """Loads the current investigative interests."""
        if not self.profile_path.exists():
            return InterestProfile()
        
        with open(self.profile_path, 'r') as f:
            data = json.load(f)
            return InterestProfile(**data)

    def seed_agenda_grains(self):
        """
        Generates 'Truth Seeds' based on the Interest Profile.
        Injects them into the MasterOutpostQueue with high gravity.
        """
        profile = self.load_profile()
        if not profile.keywords and not profile.entities:
            logger.warning("No agenda found. Run 'bridge.py onboard' to seed the Nexus intent.")
            return 0

        seeds_generated = 0
        
        # 1. Generate Perimetric Inquiry Grains
        for perimeter in profile.perimeters:
            grain_id = f"agenda:perimeter:{uuid.uuid4().hex[:8]}"
            title = f"Structural Audit: {perimeter}"
            payload = {
                "type": "AgendaSeed",
                "focus": perimeter,
                "strategy": "Recursive discovery of linked entities",
                "keywords": profile.keywords
            }
            
            # High Gravity (10.0) for Agenda-driven tasks
            if self.queue.enqueue_grain(
                grain_id=grain_id,
                title=title,
                payload=payload,
                gravity=10.0,
                probe_id="AGENDA_CONTROLLER"
            ):
                seeds_generated += 1

        # 2. Generate Entity-Specific Tracking Grains
        for entity in profile.entities:
            grain_id = f"agenda:entity:{uuid.uuid4().hex[:8]}"
            title = f"Target Investigation: {entity}"
            payload = {
                "type": "AgendaSeed",
                "focus": entity,
                "strategy": "Cross-reference with volatility spikes",
                "keywords": profile.keywords
            }
            
            if self.queue.enqueue_grain(
                grain_id=grain_id,
                title=title,
                payload=payload,
                gravity=15.0, # Entity tracking is max priority
                probe_id="AGENDA_CONTROLLER"
            ):
                seeds_generated += 1

        logger.info(f"Agenda Seeding Complete. {seeds_generated} Truth Seeds injected into the Nexus.")
        return seeds_generated

    def propose_expansion(self, linked_topic: str):
        """
        [STUB] Human-in-the-Loop Expansion logic.
        Will be used by the Reporter agent to suggest new agenda items.
        """
        # In a real implementation, this would stage a suggestion for bridge.py agenda --approve
        logger.info(f"Expansion Proposed: {linked_topic}. Awaiting Sovereign Approval.")
        pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    controller = AgendaController()
    controller.seed_agenda_grains()
