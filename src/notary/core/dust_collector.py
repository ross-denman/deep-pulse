import json
import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("dust_collector")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH = PROJECT_ROOT / "harvest" / "notary_state.db"

# Sample Archival Training Data (Sprint 01-14)
ARCHIVAL_DATA = [
    {
        "id": "training:hormuz:01",
        "title": "Archival Verification: Hormuz Straight Pulse (2026-02-15)",
        "gravity": 1.2,
        "payload": {
            "source_url": "https://archive.notary.mesh/intel/hormuz/signal-044",
            "observation": "Detected unusual cavitation patterns in Sector 4."
        },
        "answer_key": "VERIFIED: CAVITATION_CONFIRMED"
    },
    {
        "id": "training:weather:04",
        "title": "Archival Verification: Tehran Temperature Spike (2026-03-22)",
        "gravity": 0.8,
        "payload": {
            "source_url": "https://weather.archive.ir/tehran/stations/v04",
            "observation": "Reported 44C at midnight. Anomaly check required."
        },
        "answer_key": "HUMILITY: INCONCLUSIVE (SENSOR_MALFUNCTION)"
    },
    {
        "id": "training:corporate:66",
        "title": "Corporate Filing Audit: Nexus Core Holdings (2025-Q4)",
        "gravity": 1.5,
        "payload": {
            "source_url": "https://sec.archive.notary/filings/nexus-core-q4-2025",
            "observation": "Revenue listed as 0 Grains despite active lease payouts."
        },
        "answer_key": "VERIFIED: IRREGULARITY_FOUND"
    },
    {
        "id": "training:lexicon:12",
        "title": "Lexicon Hardening Check: 'The Nexus' Rebranding Pulse",
        "gravity": 1.0,
        "payload": {
            "source_url": "https://history.soul-ledger/sprint-13/lexicon-update",
            "observation": "Was 'Primary Engine' officially retired on 2026-04-08?"
        },
        "answer_key": "VERIFIED: REBRANDED_SUCCESSFUL"
    }
]

class DustCollector:
    """Hybrid script for seeding the Training Board with archival tasks."""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        
    def seed_training_tasks(self):
        """Injects archival tasks into the training_inquiries table."""
        with sqlite3.connect(self.db_path) as conn:
            for task in ARCHIVAL_DATA:
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO training_inquiries 
                        (inquiry_id, title, payload, answer_key, gravity, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        task["id"],
                        task["title"],
                        json.dumps(task["payload"]),
                        task["answer_key"],
                        task["gravity"],
                        datetime.now(timezone.utc).isoformat()
                    ))
                    logger.info(f"Seeded training task: {task['id']}")
                except Exception as e:
                    logger.error(f"Failed to seed task {task['id']}: {e}")
            
    def run(self):
        """Main execution loop for the hybrid collector."""
        logger.info("Executing DustCollector: Archival Seeding Cycle...")
        self.seed_training_tasks()
        logger.info("DustCollector Cycle Complete.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = DustCollector()
    collector.run()
