import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

# Robust PROJECT_ROOT calculation
_current_file = Path(__file__).resolve()
if "src" in _current_file.parts:
    # soul-ledger: /src/public/core/scent_engine.py -> 3 parents up
    PROJECT_ROOT = _current_file.parent.parent.parent.parent
else:
    # deep-pulse: /core/scent_engine.py -> 2 parents up
    PROJECT_ROOT = _current_file.parent.parent

SCENT_REGISTRY = PROJECT_ROOT / "harvest" / "scent_registry.json"

from src.public.storage.state_machine import MeshStateMachine
from src.public.core.reputation import ReputationService, SOVEREIGN_TREASURY_ID

logger = logging.getLogger("scent_engine")

class ScentEngine:
    """
    The Intelligence Cascade Daemon.
    Monitors the Master Chronicle for 'Scented' entities and spawns verification swarms.
    """
    def __init__(self):
        self.state_machine = MeshStateMachine()
        self.rep_service = ReputationService()
        self._load_registry()

    def _load_registry(self):
        if SCENT_REGISTRY.exists():
            with open(SCENT_REGISTRY, "r") as f:
                self.registry = json.load(f)
        else:
            self.registry = {"scents": {}} # keyword -> {owner_id, budget, active}

    def _save_registry(self):
        SCENT_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
        with open(SCENT_REGISTRY, "w") as f:
            json.dump(self.registry, f, indent=2)

    def purchase_scent(self, auditor_id: str, keyword: str, budget: int = 50) -> bool:
        """Auditor pays grains to 'Scent' a keyword for automated cascading."""
        if self.rep_service.spend_grains(auditor_id, budget, f"Scent Registration: {keyword}"):
            self.registry["scents"][keyword.lower()] = {
                "owner_id": auditor_id,
                "budget": budget,
                "active": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            self._save_registry()
            logger.info(f"Scent Registered: '{keyword}' by {auditor_id} (Budget: {budget})")
            return True
        return False

    def process_pulse(self, pulse: Dict[str, Any]):
        """Scans a single pulse for scented keywords and triggers cascades."""
        payload_str = json.dumps(pulse.get("data", {})).lower()
        # print(f"DEBUG: Processing pulse {pulse.get('id')}. Payload: {payload_str}")
        
        triggered_count = 0
        MAX_SUB_INQUIRIES = 3 # Hard Cap as per User Request

        # print(f"DEBUG: Active scents: {list(self.registry['scents'].keys())}")
        for keyword, config in self.registry["scents"].items():
            if not config["active"]: continue
            
            if keyword in payload_str:
                logger.info(f"✨ SCENT TRIGGERED: '{keyword}' found in pulse {pulse.get('id')}")
                # print(f"DEBUG: Scent triggered for '{keyword}'")
                
                # Identify potential 'Associates' or 'Entities' in the payload
                entities = pulse.get("data", {}).get("entities", [])
                # print(f"DEBUG: Entities found: {entities}")
                
                for entity in entities:
                    if triggered_count >= MAX_SUB_INQUIRIES:
                        logger.warning(f"Scent Cascade Capped: Max {MAX_SUB_INQUIRIES} reached for '{keyword}'")
                        break
                        
                    # Don't trigger on the keyword itself
                    if entity.lower() == keyword: continue
                    
                    inq_id = f"cascade_{uuid.uuid4().hex[:8]}"
                    title = f"Verification Cascade: {entity} (Ref: {pulse.get('id')})"
                    
                    # Spawn a paid inquiry from the scent owner's budget
                    if self.state_machine.sow_inquiry(
                        inquiry_id=inq_id,
                        title=title,
                        gravity=8.0, # High gravity for cascades
                        grain_bounty=10, # Sub-inquiry cost
                        payer_id=config["owner_id"],
                        payload={"parent_pulse": pulse.get("id"), "trigger_keyword": keyword}
                    ):
                        triggered_count += 1
                        logger.info(f"  ↳ Cascade Spawned: {inq_id} for entity '{entity}'")
                    
                # If budget spent, deactivate
                # (In this MVP we just decrement a flat count or check balance)
                # For now, scents stay active until balance hits 0 or manual deactivation.
