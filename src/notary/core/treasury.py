import logging
from typing import Tuple
from src.public.core.reputation import ReputationService, SOVEREIGN_TREASURY_ID

logger = logging.getLogger("notary_treasury")

class Treasury:
    """
    The Grain Sink & Burn Controller.
    Manages the permanent destruction of grains to combat inflation.
    """

    @staticmethod
    def calculate_split(amount: int) -> Tuple[int, int]:
        """Calculates the 10/90 split for the Grain Sink.
        
        Returns:
            (burn_amount, bounty_amount)
        """
        burn = max(1, int(amount * 0.1)) # Minimum 1 grain burn
        bounty = amount - burn
        return burn, bounty

    def execute_sow_spend(self, payer_id: str, total_amount: int, inquiry_id: str) -> bool:
        """Executes the sow-and-burn protocol for a user-initiated inquiry.
        
        Args:
            payer_id: The Auditor ID paying for the inquiry.
            total_amount: The total grains spent.
            inquiry_id: The ID of the inquiry being funded.
            
        Returns:
            True if successful.
        """
        rep_service = ReputationService()
        burn, bounty = self.calculate_split(total_amount)

        # 1. Deduct total amount from Payer
        if not rep_service.spend_grains(payer_id, total_amount, f"Sowing inquiry {inquiry_id}"):
            logger.error(f"Sow Failed: Auditor {payer_id} insufficient balance for {total_amount} Grains")
            return False

        # 2. The 'Burn' is implicitly handled by not awarding the burn_amount anywhere.
        # However, we log it for the "Economic Ledger" (The mental lighthouse).
        logger.info(f"🔥 GRAIN BURN: {burn} Grains destroyed from {payer_id} (Inquiry: {inquiry_id})")
        logger.info(f"💰 BOUNTY ALLOCATED: {bounty} Grains moved to Inquiry {inquiry_id} Escrow")
        
        return True
