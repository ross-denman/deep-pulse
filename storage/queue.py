import sqlite3
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("master_queue")

# Robust PROJECT_ROOT calculation to handle flattened public repo vs nested private repo
_current_file = Path(__file__).resolve()
if "src" in _current_file.parts:
    # soul-ledger: /src/public/storage/queue.py -> 3 parents up
    PROJECT_ROOT = _current_file.parent.parent.parent.parent
else:
    # deep-pulse: /storage/queue.py -> 2 parents up
    PROJECT_ROOT = _current_file.parent.parent

DB_PATH = PROJECT_ROOT / "harvest" / "inquiry_queue.db"

class InquiryQueue:
    """
    SQLite-based staging area for harvested Truth Seeds.
    Prioritizes ingestion by gravity and manages Scent TTL.
    """
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS queue (
                    grain_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source_chaff TEXT, -- URL or CID of raw data
                    surprise_index REAL DEFAULT 0.0,
                    gravity REAL DEFAULT 0.0,
                    payload TEXT NOT NULL,
                    status TEXT DEFAULT 'QUEUED', -- QUEUED, INQUIRY_OPEN, GROUNDING_IN_PROGRESS, COMPLETED, ARCHIVED
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    claimed_by TEXT,
                    probe_id TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON queue(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gravity ON queue(gravity DESC)")

    def enqueue_grain(self, grain_id: str, title: str, payload: Dict[str, Any], 
                      source_chaff: str = "", surprise_index: float = 0.0,
                      gravity: float = 5.0, probe_id: str = "GENERIC_PROBE"):
        """Adds a new discovery to the prioritized staging area."""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=72) # Scent TTL
        
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute("""
                    INSERT INTO queue (grain_id, title, source_chaff, surprise_index, gravity, payload, created_at, expires_at, probe_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (grain_id, title, source_chaff, surprise_index, gravity, json.dumps(payload), 
                      now.isoformat(), expires.isoformat(), probe_id))
                logger.info(f"Enqueued grain {grain_id} (Gravity: {gravity}, Surprise: {surprise_index})")
                return True
            except sqlite3.IntegrityError:
                logger.warning(f"Grain {grain_id} already exists in queue.")
                return False

    def list_open_inquiries(self) -> List[Dict[str, Any]]:
        """Returns grains ready for mesh consensus."""
        self._cleanup_expired()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT grain_id as id, title, gravity, status, source_chaff, surprise_index, payload, created_at, expires_at, probe_id 
                FROM queue 
                WHERE status = 'QUEUED' OR status = 'INQUIRY_OPEN'
                ORDER BY gravity DESC, created_at ASC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def claim_grain(self, grain_id: str, outpost_id: str, lease_hours: int = 24) -> Optional[str]:
        """Marks a grain as claimed by a specific outpost."""
        expires = datetime.now(timezone.utc) + timedelta(hours=lease_hours)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE queue 
                SET status = 'GROUNDING_IN_PROGRESS', claimed_by = ?, expires_at = ?
                WHERE grain_id = ? AND (status = 'QUEUED' OR status = 'INQUIRY_OPEN')
            """, (outpost_id, expires.isoformat(), grain_id))
            
            if cursor.rowcount > 0:
                return expires.isoformat()
        return None

    def complete_grain(self, grain_id: str):
        """Marks a grain as settled and archived from the active queue."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE queue SET status = 'COMPLETED' WHERE grain_id = ?", (grain_id,))
            logger.info(f"Grain {grain_id} marked as completed in queue.")

    def _cleanup_expired(self):
        """Archives grains that hit their Scent TTL or lease expiry."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            # Revert expired claims
            conn.execute("""
                UPDATE queue 
                SET status = 'INQUIRY_OPEN', claimed_by = NULL 
                WHERE status = 'GROUNDING_IN_PROGRESS' AND expires_at < ?
            """, (now,))
            
            # Archive stale uncorroborated scents
            conn.execute("""
                UPDATE queue 
                SET status = 'ARCHIVED' 
                WHERE (status = 'QUEUED' OR status = 'INQUIRY_OPEN') AND expires_at < ?
            """, (now,))

MasterOutpostQueue = InquiryQueue

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    q = InquiryQueue()
    q.enqueue_grain("test_id", "Meta Variance Found", {"link": "https://example.com"}, gravity=10.0)
    print(q.list_open_inquiries())
