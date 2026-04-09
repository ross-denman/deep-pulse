#!/usr/bin/env python3
"""
The Chronicle - Meshtastic Heartbeat (radio.py)

The "Silent Pulse": Low-bandwidth radio broadcast logic for 
sending truth summaries over LoRa/Meshtastic.

This allows the 'Institutional Mind' to haunt the local mesh 
independently of the internet.
"""

import logging
import json
import base64
import zlib
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LEDGER_FILE = PROJECT_ROOT / "harvest" / "chronicle.jsonld"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("radio-heartbeat")

class SilentPulse:
    """Generates ultra-compressed summaries for radio broadcast."""

    def __init__(self, outpost_id: str):
        self.outpost_id = outpost_id[:8]

    def create_truth_summary(self, max_bytes: int = 200) -> bytes:
        """
        Creates a super-compressed summary of the latest ledger state.
        
        Format:
        [outpost_id:4][count:2][verified:2][last_cid_short:8][anomaly_flag:1]
        """
        from core.chronicle import read_ledger
        ledger = read_ledger()
        
        total = len(ledger)
        verified = sum(1 for e in ledger if e.get("metadata", {}).get("status") == "verified")
        last_cid = ledger[-1]["id"] if ledger else "0" * 64
        
        summary = {
            "n": self.outpost_id,
            "t": total,
            "v": verified,
            "l": last_cid[:8],
            "a": any("ANOMALY" in str(e) for e in ledger[-5:]) # Last 5 pulses
        }
        
        # Compress
        raw_json = json.dumps(summary, separators=(',', ':'))
        compressed = zlib.compress(raw_json.encode('utf-8'))
        
        logger.info(f"Generated Silent Pulse: {len(raw_json)} bytes -> {len(compressed)} bytes.")
        return compressed

    def broadcast_mock(self, data: bytes):
        """Mock Meshtastic broadcast."""
        encoded = base64.b64encode(data).decode('utf-8')
        logger.info(f"[TX] BROADCASTING SILENT PULSE [LoRa]: {encoded}")
        print(f"\n{'-'*40}")
        print(f"[TX] RADIO HEARTBEAT (Silent Pulse)")
        print(f"Payload: {encoded}")
        print(f"Size: {len(data)} bytes")
        print(f"{'-'*40}\n")

if __name__ == "__main__":
    from core.identity import load_identity
    identity = load_identity()
    pulse = SilentPulse(identity.outpost_id)
    payload = pulse.create_truth_summary()
    pulse.broadcast_mock(payload)
