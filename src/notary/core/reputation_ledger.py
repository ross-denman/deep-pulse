import logging
from src.public.core.reputation import ReputationService, SOVEREIGN_TREASURY_ID

logger = logging.getLogger("notary_economy")

class NotaryEconomy:
    """Manages the State-Orchestrated Economy (Treasury, Payouts, Slashing)."""
    
    def __init__(self):
        self.rep_service = ReputationService()

    def escrow_bounty(self, inquiry_id: str, amount: int) -> bool:
        """Deducts bounty from Treasury and locks it."""
        return self.rep_service.spend_grains(SOVEREIGN_TREASURY_ID, amount, f"Inquiry Escrow: {inquiry_id}")

    def refund_bounty(self, inquiry_id: str, amount: int, reason: str = "Refund"):
        """Returns bounty to Treasury."""
        self.rep_service.award_grains(SOVEREIGN_TREASURY_ID, amount, f"{reason}: {inquiry_id}")

    def collect_dust(self, amount: int, inquiry_id: str):
        """Returns rounding remainders to Treasury as network fees."""
        if amount > 0:
            self.rep_service.award_grains(SOVEREIGN_TREASURY_ID, amount, f"Network Fee (Dust): {inquiry_id}")

    def settle_payout(self, outpost_id: str, amount: int, reason: str):
        """Awards grains to a participant (Finder or Verifier)."""
        self.rep_service.award_grains(outpost_id, amount, reason)
        # All successful contributions trigger a Liveness Boost (+0.05)
        outpost = self.rep_service.get_outpost(outpost_id)
        if outpost:
            outpost.apply_liveness_event(success=True)

    def apply_lease_penalty(self, outpost_id: str, inquiry_id: str):
        """Applies liveness penalty for expired/failed leases."""
        outpost = self.rep_service.get_outpost(outpost_id)
        if outpost:
            logger.warning(f"Slashing Liveness for Outpost {outpost_id} due to expiration on {inquiry_id}")
            outpost.apply_liveness_event(success=False)
