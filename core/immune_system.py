import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

from src.public.core.identity import verify_signature_with_pubkey
from src.public.core.reputation import ReputationService, ReputationTier
from src.public.core.chronicle import canonical_json

logger = logging.getLogger("notary_immune_system")

SUBMISSION_LIMITS = {
    ReputationTier.UNVERIFIED: 10,
    ReputationTier.SCOUT: 50,
    ReputationTier.AUDITOR: 0, # Unlimited
}

class MeshImmuneSystem:
    """Guards the Discovery Mesh from malicious or erratic activity."""

    def __init__(self):
        self.rep_service = ReputationService()
        self._submission_history: Dict[str, List[float]] = {}

    def validate_auditor_handshake(self, outpost_id: str, signature: str, message: str) -> bool:
        """Verifies that an Auditor's claim handshake is cryptographically sound."""
        outpost_rep = self.rep_service.get_outpost(outpost_id)
        if not outpost_rep:
            return False
            
        # Liveness Gatekeeping
        if outpost_rep.liveness_score < 0.5: # Hard floor for any claim
            logger.warning(f"Handshake rejected: Outpost {outpost_id} liveness too low (%.2f)", 
                           outpost_rep.liveness_score)
            return False

        return verify_signature_with_pubkey(outpost_rep.public_key_hex, message.encode(), signature)

    def validate_proof(self, outpost_id: str, payload: Dict[str, Any], signature: str) -> bool:
        """Validates the final discovery package submitted for settlement."""
        outpost_rep = self.rep_service.get_outpost(outpost_id)
        if not outpost_rep:
            return False

        signable_bytes = canonical_json(payload)
        return verify_signature_with_pubkey(outpost_rep.public_key_hex, signable_bytes, signature)

    def get_friction_multiplier(self, source_url: str) -> float:
        """Calculates bounty multiplier ($SR-G) based on source reliability."""
        source_rep = self.rep_service.get_source(source_url)
        if source_rep.status == "VERIFIED":
            return 1.0
        elif source_rep.status == "PROBATIONARY":
            return 0.8
        else: # SPECULATIVE / UNKNOWN
            return 0.5 # Thermodynamic Friction (50% bounty)

    def get_required_verifiers(self, source_url: str) -> int:
        """Determines verifier count for consensus (2+1 vs 3+1)."""
        source_rep = self.rep_service.get_source(source_url)
        # Speculative sources have a higher forensic floor
        if source_rep.status == "SPECULATIVE":
            return 3 # 3+1 Rule
        return 2 # 2+1 Rule

    def _check_velocity(self, outpost_id: str, tier: Any) -> bool:
        """Enforces tiered submission limits."""
        tier_val = tier.value if hasattr(tier, "value") else int(tier)
        limit = SUBMISSION_LIMITS.get(tier_val, 1)
        if limit == 0: return True

        now = time.time()
        hour_ago = now - 3600
        self._submission_history[outpost_id] = [t for t in self._submission_history.get(outpost_id, []) if t > hour_ago]

        if len(self._submission_history[outpost_id]) >= limit:
            return False
            
        self._submission_history[outpost_id].append(now)
        return True
