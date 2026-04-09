import sys
import os
from pathlib import Path

# Fix python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.public.core.reputation import ReputationService

if __name__ == "__main__":
    rep = ReputationService()
    # Force save to update schema and types
    rep.save_state()
    print("Reputation state updated to float scores.")
    
    # Check a specific outpost
    outpost = rep.get_outpost("AUDITOR_TEST")
    if outpost:
        print(f"AUDITOR_TEST Status: {outpost.tier.name} (Score: {outpost.score})")
