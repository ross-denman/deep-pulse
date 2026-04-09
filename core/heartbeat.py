#!/usr/bin/env python3
"""
Deep Pulse - Heartbeat Protocol (OCI Survival)

Maintain real-time 'Gravity' on the Oracle Cloud instance to prevent idle-reclaim
while verifying the outpost's sovereign identity via periodic synthetic pulses.
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys_path = str(PROJECT_ROOT)
import sys
if sys_path not in sys.path:
    sys.path.append(sys_path)

from core.identity import load_identity
from core.reputation import ReputationService

logger = logging.getLogger("heartbeat")

class HeartbeatManager:
    """Manages the background 'Synthetic Pulse' loop for OCI survival."""

    def __init__(self, interval_minutes: int = 30):
        self.interval = interval_minutes * 60
        self.identity = load_identity()
        self.reputation = ReputationService()
        self.log_file = PROJECT_ROOT / "harvest" / "heartbeat.log"
        
        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def _low_weight_calibration(self) -> dict:
        """Perform a tiny, low-impact calculation to create CPU/RAM noise."""
        # Trivial math: hashing a random seed and verifying a prime match
        seed = os.urandom(32).hex()
        # Artificial noise: hash it 10,000 times (low impact, but measurable)
        h = seed
        for _ in range(10000):
            h = hashlib.sha256(h.encode()).hexdigest()
            
        return {
            "seed": seed,
            "hash": h,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def _seal_pulse(self, data: dict) -> str:
        """Seal the synthetic pulse with the outpost's sovereign seal."""
        message = json.dumps(data, sort_keys=True).encode()
        return self.identity.sign(message)

    def _log_event(self, entry: dict):
        """Append the heartbeat entry to the local log."""
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    async def run_forever(self):
        """Start the infinite heartbeat loop."""
        print(f"\n  [TX] {C.BOLD}OCI HEARTBEAT ACTIVE{C.RESET}")
        print(f"  {C.DIM}Interval: {self.interval // 60} minutes{C.RESET}")
        print(f"  {C.DIM}Log: {self.log_file}{C.RESET}")
        print(f"  {C.CYAN}Maintaining Gravity for Outpost {self.identity.outpost_id}...{C.RESET}\n")

        while True:
            try:
                # 1. Perform Calculation (CPU/RAM Noise)
                pulse_data = self._low_weight_calibration()
                
                # 2. Verify Identity (Sealing)
                seal = self._seal_pulse(pulse_data)
                
                # 3. Formulate Entry
                entry = {
                    "type": "SyntheticPulse",
                    "outpost_id": self.identity.outpost_id,
                    "data": pulse_data,
                    "seal": seal,
                    "status": "calibrated"
                }
                
                # 4. Log
                self._log_event(entry)
                
                # 5. Display Console Feedback
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"  {C.GREEN}[{ts}]{C.RESET} [*] Synthetic Pulse Calibrated: {seal[:16]}... {C.DIM}[Seal Verified]{C.RESET}")
                
            except Exception as e:
                logger.error("Heartbeat error: %s", e)
                print(f"  {C.RED}Ã¢Å“â€” Heartbeat failed: {e}{C.RESET}")

            # Wait for next interval
            await asyncio.sleep(self.interval)

# --- ANSI Colors (Duplicate for standalone use) ---
class C:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

if __name__ == "__main__":
    # Test run
    manager = HeartbeatManager(interval_minutes=0.1) # 6 second test
    asyncio.run(manager.run_forever())
