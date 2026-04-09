import sys
import os
import shutil
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
import uuid

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Clean up previous test state
HARVEST_DIR = PROJECT_ROOT / "harvest"
for f in ["notary_state.db", "leases.json", "reputation.json", "scent_registry.json"]:
    p = HARVEST_DIR / f
    if p.exists(): os.remove(p)

from src.public.core.reputation import ReputationService
from src.notary.core.state_machine import NotaryStateMachine
from src.private.agents.scent_engine import ScentEngine

# Mocking LeaseManager to avoid flask dependency in test
class MockLeaseManager:
    def __init__(self):
        self.LEASE_FILE = PROJECT_ROOT / "harvest" / "leases.json"
        
    def has_active_lease(self, auditor_id: str) -> bool:
        if not self.LEASE_FILE.exists(): return False
        with open(self.LEASE_FILE, "r") as f:
            leases = json.load(f)
        if auditor_id not in leases: return False
        expiry = datetime.fromisoformat(leases[auditor_id])
        return datetime.now(timezone.utc) < expiry

    def purchase_lease(self, auditor_id: str, hours: int = 4):
        rs = ReputationService()
        if rs.spend_grains(auditor_id, 25, "Test Lease"):
            expiry = datetime.now(timezone.utc) + timedelta(hours=hours)
            leases = {}
            if self.LEASE_FILE.exists():
                with open(self.LEASE_FILE, "r") as f: leases = json.load(f)
            leases[auditor_id] = expiry.isoformat()
            with open(self.LEASE_FILE, "w") as f: json.dump(leases, f, indent=2)
            return expiry
        return None

lease_manager = MockLeaseManager()

def test_grain_sink():
    print("--- Testing Grain Sink (Sow-and-Burn) ---")
    rs = ReputationService()
    rs.register_outpost("AUDITOR_TEST", "KEY_TEST")
    rs.award_grains("AUDITOR_TEST", 100, "Setup")
    sm = NotaryStateMachine()
    
    auditor_id = "AUDITOR_TEST"
    initial_balance = rs.get_outpost(auditor_id).grain_balance
    print(f"Initial Balance: {initial_balance}")
    
    # Sow a 50 Grain Inquiry
    # Expected: 5 burn (10%), 45 bounty (90%)
    success = sm.sow_inquiry(
        inquiry_id="test_burn_123",
        title="Burn Test Inquiry",
        grain_bounty=50,
        payer_id=auditor_id
    )
    
    if success:
        rs.load_state() # Explicitly reload state from disk
        outpost = rs.get_outpost(auditor_id)
        new_balance = outpost.grain_balance
        inquiry = sm.get_inquiry("test_burn_123")
        bounty = inquiry["grain_bounty"]
        
        print(f"New Balance: {new_balance} (Spent: {initial_balance - new_balance})")
        print(f"Inquiry Bounty: {bounty}")
        
        if (initial_balance - new_balance) == 50 and bounty == 45:
            print("✅ PASS: 10% Burn confirmed (5 Grains destroyed).")
        else:
            print("❌ FAIL: Burn math incorrect.")
    else:
        print("❌ FAIL: Inquiry sowing failed.")

def test_scent_cascade():
    print("\n--- Testing Scent Engine (Cascade Hard Cap) ---")
    se = ScentEngine()
    sm = NotaryStateMachine()
    
    # 1. Register Scent for 'Ghalibaf'
    # Budget is 25 (cost of lease) + 50 (burn test) = 75 spent. 100 - 75 = 25 left? 
    # Let's award more grains first.
    rs = ReputationService()
    rs.award_grains("AUDITOR_TEST", 200, "Refill for Scent Test")
    
    se.purchase_scent("AUDITOR_TEST", "Ghalibaf", budget=50)
    
    # 2. Simulate Pulse with matching keyword and 5 entities
    pulse = {
        "id": "pulse_scent_test",
        "data": {
            "title": "Ghalibaf visits Beirut",
            "entities": ["Ghalibaf", "Hezbollah", "Nasrallah", "Berri", "Micro-Entity-4", "Micro-Entity-5"]
        }
    }
    
    se.process_pulse(pulse)
    
    # 3. Check for sub-inquiries
    open_market = sm.list_open_market()
    print(f"Open Market Entries: {len(open_market)}")
    for i in open_market:
        print(f"  - {i['id']}: {i['title']}")
    cascades = [i for i in open_market if "cascade_" in i["id"]]
    
    print(f"Total Cascades Spawned: {len(cascades)}")
    if len(cascades) == 3:
        print("✅ PASS: Hard Cap of 3 sub-inquiries enforced.")
    else:
        print(f"❌ FAIL: Expected 3 cascades, found {len(cascades)}.")

def test_detective_lease():
    print("\n--- Testing Detective Lease Gating ---")
    auditor_id = "AUDITOR_TEST"
    rs = ReputationService()
    rs.load_state()
    rs.award_grains(auditor_id, 100, "Refill for Lease Test")
    
    # Initially should not have lease
    if not lease_manager.has_active_lease(auditor_id):
        print("✅ PASS: Initial lease state is False.")
    else:
        print("❌ FAIL: Initial lease state is True.")
        
    # Purchase lease
    expiry = lease_manager.purchase_lease(auditor_id)
    if expiry:
        print(f"Lease Purchased. Expiry: {expiry}")
        if lease_manager.has_active_lease(auditor_id):
            print("✅ PASS: Lease active after purchase.")
        else:
            print("❌ FAIL: Lease not active after purchase.")
    else:
        print("❌ FAIL: Lease purchase failed.")

if __name__ == "__main__":
    test_grain_sink()
    test_scent_cascade()
    test_detective_lease()
