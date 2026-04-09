import sqlite3
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("auditor_queue")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH = PROJECT_ROOT / "harvest" / "auditor_local.db"

class AuditorQueue:
    """
    Local staging area for an Auditor's work.
    Stores claims and findings before they are gossiped or submitted to the Notary.
    """
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS local_work (
                    inquiry_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT DEFAULT 'CLAIMED',
                    payload TEXT,
                    claim_data TEXT,
                    created_at TEXT NOT NULL
                )
            """)

    def save_local_claim(self, inquiry_id: str, title: str, claim_data: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO local_work (inquiry_id, title, claim_data, created_at)
                VALUES (?, ?, ?, ?)
            """, (inquiry_id, title, json.dumps(claim_data), datetime.now(timezone.utc).isoformat()))

    def list_open_inquiries(self) -> List[Dict[str, Any]]:
        """Shim for HuntController compatibility."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT inquiry_id as id, title FROM local_work WHERE status = 'CLAIMED'")
            return [dict(row) for row in cursor.fetchall()]
            
    def complete_grain(self, id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE local_work SET status = 'COMPLETED' WHERE inquiry_id = ?", (id,))
