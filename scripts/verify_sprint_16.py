import sys
import json
import requests
import time
from pathlib import Path

# Fix paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.public.core.reputation import ReputationService, ReputationTier

BASE_URL = "http://127.0.0.1:4110"
TEST_ID = "VERIFY_TEST"

def run_verification():
    print("═══ Strategic Verification Run (Sprint 16) ═══")
    rep_service = ReputationService()
    
    # 1. Identity Initialization
    print("\n1. Initialization Check...")
    if TEST_ID in rep_service._outposts:
        del rep_service._outposts[TEST_ID]
        rep_service.save_state()
    
    # Register new
    rep_service.register_outpost(TEST_ID, "VERIFY_KEY_HEX")
    outpost = rep_service.get_outpost(TEST_ID)
    print(f"   Identity Initialized: {TEST_ID}")
    print(f"   Score: {outpost.score}, Tier: {outpost.tier.name}")
    assert outpost.tier == ReputationTier.UNVERIFIED
    
    # 2. Firewall Check
    print("\n2. Firewall Check...")
    payload = {
        "outpost_id": TEST_ID,
        "inquiry_id": "any_id"
    }
    resp = requests.post(f"{BASE_URL}/inquiries/claim", json=payload)
    print(f"   POST /inquiries/claim (Provisional): {resp.status_code}")
    print(f"   Message: {resp.json().get('message')}")
    assert resp.status_code == 403
    assert resp.json().get("status") == "LEVEL_UP_REQUIRED"
    
    # 3. The 10-Task Sprint
    print("\n3. The 10-Task Sprint...")
    tasks_resp = requests.get(f"{BASE_URL}/api/v1/training")
    tasks = tasks_resp.json().get("tasks", [])
    
    # Find the Hormuz task specifically
    hormuz_task = next((t for t in tasks if "hormuz" in t["id"]), None)
    if not hormuz_task:
        print("   FAILED: Hormuz task not found on board.")
        return
        
    training_id = hormuz_task["id"]
    discovery_text = "CAVITATION_CONFIRMED"
    
    for i in range(1, 11):
        submit_payload = {
            "outpost_id": TEST_ID,
            "inquiry_id": training_id,
            "discovery": discovery_text
        }
        resp = requests.post(f"{BASE_URL}/api/v1/training/submit", json=submit_payload)
        data = resp.json()
        
        # We need to refresh OUTPOST repo state from the server/file if we want to see grains here
        # or just trust the API response. API response has 'current_rep'.
        print(f"   Task {i:02}: {data['status']} | Rep: {data['current_rep']}")
        
    # Check status after 10 tasks via the reputation service (force reload)
    rep_service.load_state() 
    final_outpost = rep_service.get_outpost(TEST_ID)
    print(f"   Final Score: {final_outpost.score}")
    print(f"   Final Tier: {final_outpost.tier.name}")
    assert final_outpost.tier == ReputationTier.AUDITOR
    assert final_outpost.grain_balance >= 10
    
    # 4. The "Healing" Drift
    print("\n4. Healing Drift Check...")
    final_outpost.score = -0.1
    print(f"   Simulating Downtime: Score manually set to {final_outpost.score}")
    rep_service.apply_yield_to_all()
    print(f"   After Decay Pulse: Score is {final_outpost.score}")
    # -0.1 + 0.01 = -0.09
    assert round(final_outpost.score, 2) == -0.09
    
    print("\n✅ ALL SPRINT 16 VERIFICATIONS PASSED.")

if __name__ == "__main__":
    try:
        run_verification()
    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        sys.exit(1)
