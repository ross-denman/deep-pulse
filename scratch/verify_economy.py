import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.public.core.reputation import ReputationService, SOVEREIGN_TREASURY_ID
from src.notary.core.state_machine import NotaryStateMachine

def test_economy():
    print("--- 🏴‍☠️ Testing Sovereign Economy ---")
    
    # 1. Initialize Service & Treasury
    rep_service = ReputationService()
    treasury = rep_service.get_outpost(SOVEREIGN_TREASURY_ID)
    print(f"Treasury Initialized: {treasury is not None}")
    print(f"Treasury Balance: {treasury.grain_balance if treasury else 0} Grains")
    
    # 2. Sow Inquiry (Escrow)
    sm = NotaryStateMachine()
    inq_id = "test-inquiry-001"
    bounty = 100
    
    print(f"\nSowing Inquiry: {inq_id} (Bounty: {bounty})")
    success = sm.sow_inquiry(inq_id, "Geopolitical Audit", gravity=8.0, grain_bounty=bounty)
    print(f"Sow Success: {success}")
    
    rep_service.load_state() # Reload from disk
    treasury = rep_service.get_outpost(SOVEREIGN_TREASURY_ID)
    print(f"Treasury Balance after Escrow: {treasury.grain_balance} Grains (Expected: 24900)")
    
    # 3. Simulate Participants
    finder_id = "auditor-01"
    verifier1_id = "verifier-01"
    verifier2_id = "verifier-02"
    
    rep_service.register_outpost(finder_id, "KEY1")
    rep_service.register_outpost(verifier1_id, "KEY2")
    rep_service.register_outpost(verifier2_id, "KEY3")
    
    # Claim and Complete
    sm.accept_handshake(type('Handshake', (), {
        'outpost_id': finder_id,
        'inquiry_id': inq_id,
        'signature': 'SIG1',
        'timestamp': datetime.now(timezone.utc),
        'lease_hours': 1
    }))
    
    # Add Verifications
    sm.add_verification(inq_id, verifier1_id, "SIG2")
    sm.add_verification(inq_id, verifier2_id, "SIG3")
    
    # Settle
    print(f"\nSettling Inquiry: {inq_id}")
    settle_success = sm.settle_inquiry(inq_id)
    print(f"Settle Success: {settle_success}")
    
    rep_service.load_state() # Reload from disk
    # Check Balances
    f = rep_service.get_outpost(finder_id)
    v1 = rep_service.get_outpost(verifier1_id)
    v2 = rep_service.get_outpost(verifier2_id)
    t = rep_service.get_outpost(SOVEREIGN_TREASURY_ID)
    
    print(f"\nFinder ({finder_id}) Balance: {f.grain_balance} (Expected: 25 + 60 = 85)")
    print(f"Verifier 1 ({verifier1_id}) Balance: {v1.grain_balance} (Expected: 25 + 20 = 45)")
    print(f"Verifier 2 ({verifier2_id}) Balance: {v2.grain_balance} (Expected: 25 + 20 = 45)")
    print(f"Treasury Balance: {t.grain_balance} (Expected: 24900 if no dust)")
    
    # Check Liveness
    print(f"Finder Liveness: {f.liveness_score}")
    print(f"Verifier 1 Liveness: {v1.liveness_score}")

if __name__ == "__main__":
    test_economy()
