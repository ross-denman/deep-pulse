#!/usr/bin/env python3
import os
import json
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import Ledger core (from the sibling directory)
LEDGER_REPO = "/home/ubuntu/deep-ledger"
sys.path.insert(0, LEDGER_REPO)

from src.core.ledger import create_entry, append_entry
from src.core.identity import load_identity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pulse-bridge")

def bridge_all():
    history_dir = "data/history"
    if not os.path.exists(history_dir):
        logger.error(f"History directory not found: {history_dir}")
        return

    # Load Ledger identity
    try:
        identity = load_identity()
        logger.info(f"Loaded identity: {identity.node_id}")
    except Exception as e:
        logger.error(f"Failed to load ledger identity: {e}")
        return

    for filename in os.listdir(history_dir):
        if filename.endswith("_summary.json"):
            path = os.path.join(history_dir, filename)
            with open(path, "r") as f:
                summary = json.load(f)
            
            mission_id = summary.get("mission_id")
            truth_insights = summary.get("truth_insights", [])
            
            logger.info(f"Bridging mission {mission_id} ({len(truth_insights)} pulses)...")
            
            for insight in truth_insights:
                # Create a speculative ledger entry
                entry = create_entry(
                    identity=identity,
                    data={
                        "type": "TruthPulse",
                        "mission_id": mission_id,
                        "insight": insight
                    },
                    source_url=insight.get("source", "unknown"),
                    scout_id=insight.get("claim_keyword", "pulse"),
                    status="speculative"
                )
                append_entry(entry)
                logger.info(f"  Sent CID: {entry['id']}")

if __name__ == "__main__":
    bridge_all()
