import sqlite3
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.public.core.contracts import ClaimHandshake
from src.public.core.reputation import ReputationService, SOVEREIGN_TREASURY_ID
from src.notary.core.treasury import Treasury

logger = logging.getLogger("notary_state")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH = PROJECT_ROOT / "harvest" / "notary_state.db"

class NotaryStateMachine:
    """
    The Orchestrator of State for the Sovereign Notary.
    Manages the lifecycle of inquiries, claims, and settlements.
    """
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inquiries (
                    inquiry_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    gravity REAL DEFAULT 5.0,
                    grain_bounty INTEGER DEFAULT 25,
                    status TEXT DEFAULT 'OPEN', -- OPEN, CLAIMED, VERIFYING, SETTLED, EXPIRED
                    payload TEXT,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    claimed_by TEXT,
                    claim_signature TEXT,
                    claim_timestamp TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON inquiries(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gravity ON inquiries(gravity DESC)")
            
            # Verification Pool for 2+1 / 3+1 consensus
            conn.execute("""
                CREATE TABLE IF NOT EXISTS verification_pool (
                    inquiry_id TEXT,
                    outpost_id TEXT,
                    signature TEXT,
                    timestamp TEXT,
                    PRIMARY KEY (inquiry_id, outpost_id),
                    FOREIGN KEY (inquiry_id) REFERENCES inquiries(inquiry_id)
                )
            """)
            
            # Training Archive for Provisional nodes
            conn.execute("""
                CREATE TABLE IF NOT EXISTS training_inquiries (
                    inquiry_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    payload TEXT,
                    answer_key TEXT, -- The expected valid discovery
                    gravity REAL DEFAULT 1.0,
                    created_at TEXT NOT NULL
                )
            """)

    def sow_inquiry(self, inquiry_id: str, title: str, gravity: float = 5.0, 
                    grain_bounty: int = 25, payload: Optional[Dict[str, Any]] = None,
                    payer_id: str = SOVEREIGN_TREASURY_ID):
        """Notary or Auditor issues a new inquiry. Deducts bounty from Treasury or Payer."""
        treasury = Treasury()
        
        # 1. Economic Logic: Handle Spend & Burn
        if payer_id == SOVEREIGN_TREASURY_ID:
            # System-generated: Pure Escrow (No Burn for now to keep bootstrap liquidity)
            rep_service = ReputationService()
            if not rep_service.spend_grains(SOVEREIGN_TREASURY_ID, grain_bounty, f"Escrow for inquiry {inquiry_id}"):
                logger.error(f"Inquiry Rejected: Treasury Insufficient Liquidity for bounty {grain_bounty}")
                return False
            actual_bounty = grain_bounty
        else:
            # User-generated: 10/90 Sink
            if not treasury.execute_sow_spend(payer_id, grain_bounty, inquiry_id):
                return False
            _, actual_bounty = treasury.calculate_split(grain_bounty)

        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=72) # Scent TTL
        
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute("""
                    INSERT INTO inquiries (inquiry_id, title, gravity, grain_bounty, payload, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (inquiry_id, title, gravity, actual_bounty, json.dumps(payload or {}), 
                      now.isoformat(), expires.isoformat()))
                logger.info(f"Sown inquiry {inquiry_id} (Bounty: {actual_bounty} Grains Escrowed by {payer_id})")
                return True
            except sqlite3.IntegrityError:
                # Refund if DB insert fails
                rep_service = ReputationService()
                rep_service.award_grains(payer_id, grain_bounty, f"Refund: DB Failure for {inquiry_id}")
                return False

    def list_open_market(self) -> List[Dict[str, Any]]:
        """Returns all inquiries available for claim."""
        self._cleanup_expired()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT inquiry_id as id, title, gravity, grain_bounty, status, created_at, expires_at 
                FROM inquiries 
                WHERE status = 'OPEN'
                ORDER BY gravity DESC, created_at ASC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def accept_handshake(self, handshake: ClaimHandshake) -> Optional[datetime]:
        """Locks an inquiry to an Auditor via a signed handshake."""
        expires = datetime.now(timezone.utc) + timedelta(hours=handshake.lease_hours)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE inquiries 
                SET status = 'CLAIMED', 
                    claimed_by = ?, 
                    claim_signature = ?, 
                    claim_timestamp = ?,
                    expires_at = ?
                WHERE inquiry_id = ? AND status = 'OPEN'
            """, (handshake.outpost_id, handshake.signature, 
                  handshake.timestamp.isoformat(), expires.isoformat(), 
                  handshake.inquiry_id))
            
            if cursor.rowcount > 0:
                logger.info(f"Handshake accepted: {handshake.inquiry_id} claimed by {handshake.outpost_id}")
                return expires
        return None

    def get_inquiry(self, inquiry_id: str) -> Optional[Dict[str, Any]]:
        """Returns full state of a specific inquiry."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM inquiries WHERE inquiry_id = ?", (inquiry_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def add_verification(self, inquiry_id: str, outpost_id: str, signature: str):
        """Adds a verifier to the pool for an inquiry."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute("""
                    INSERT INTO verification_pool (inquiry_id, outpost_id, signature, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (inquiry_id, outpost_id, signature, now))
                logger.info(f"Verification added: Inquiry {inquiry_id} (Auditor: {outpost_id})")
                return True
            except sqlite3.IntegrityError:
                return False

    def get_verifiers(self, inquiry_id: str) -> List[str]:
        """Returns the list of verifiers for an inquiry, ordered by arrival."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT outpost_id FROM verification_pool 
                WHERE inquiry_id = ? 
                ORDER BY timestamp ASC
            """, (inquiry_id,))
            return [row[0] for row in cursor.fetchall()]

    def list_training_market(self) -> List[Dict[str, Any]]:
        """Returns archival tasks for Provisional training."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT inquiry_id as id, title, gravity, created_at 
                FROM training_inquiries 
                ORDER BY created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_training_inquiry(self, inquiry_id: str) -> Optional[Dict[str, Any]]:
        """Returns the full data + answer key for a training task."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM training_inquiries WHERE inquiry_id = ?", (inquiry_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def settle_inquiry(self, inquiry_id: str):
        """Promotes an inquiry to SETTLED and triggers 60/20/20 split."""
        from src.public.core.reputation import ReputationService, SOVEREIGN_TREASURY_ID
        rep_service = ReputationService()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM inquiries WHERE inquiry_id = ?", (inquiry_id,))
            inquiry = cursor.fetchone()
            
            if not inquiry or inquiry["status"] == "SETTLED":
                return False
                
            finder_id = inquiry["claimed_by"]
            bounty = inquiry["grain_bounty"]
            
            # Get verifiers
            verifiers = self.get_verifiers(inquiry_id)
            
            # 60/20/20 Split logic
            finder_share = int(bounty * 0.6)
            verifier_pool_total = int(bounty * 0.4)
            
            # First two verifiers get 20% each (half of the 40% pool)
            v1_share = int(verifier_pool_total / 2) if len(verifiers) >= 1 else 0
            v2_share = int(verifier_pool_total / 2) if len(verifiers) >= 2 else 0
            
            total_distributed = finder_share + v1_share + v2_share
            dust = bounty - total_distributed
            
            # 1. Award Finder
            if finder_id:
                rep_service.award_grains(finder_id, finder_share, f"Settlement: Finder for {inquiry_id}")
                rep_service.award(finder_id, "discovery", f"Settlement for {inquiry_id}")
                
            # 2. Award Verifiers
            for i, v_id in enumerate(verifiers):
                if i == 0:
                    rep_service.award_grains(v_id, v1_share, f"Settlement: Verifier1 for {inquiry_id}")
                elif i == 1:
                    rep_service.award_grains(v_id, v2_share, f"Settlement: Verifier2 for {inquiry_id}")
                
                # All verifiers get Rep/Liveness boost for contributing
                rep_service.award(v_id, "verification", f"Consensus contribution for {inquiry_id}")
                # Note: Liveness boost (+0.05) is handled by the ReputationService award logic 
                # or manually here if needed.
                outpost = rep_service.get_outpost(v_id)
                if outpost:
                    outpost.apply_liveness_event(success=True)

            # 3. Dust to Treasury
            if dust > 0:
                rep_service.award_grains(SOVEREIGN_TREASURY_ID, dust, f"Network Maintenance Fee (Dust) from {inquiry_id}")

            # 4. Finalize State
            conn.execute("UPDATE inquiries SET status = 'SETTLED' WHERE inquiry_id = ?", (inquiry_id,))
            logger.info(f"Inquiry {inquiry_id} SETTLED. Split: Finder={finder_share}, V1={v1_share}, V2={v2_share}, Dust={dust}")
            return True

    def _cleanup_expired(self):
        """Handles Lease Reversion and Liveness tracking."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            # Find expired claims to penalize liveness
            cursor = conn.execute("""
                SELECT inquiry_id, claimed_by FROM inquiries 
                WHERE status = 'CLAIMED' AND expires_at < ?
            """, (now,))
            expired_claims = cursor.fetchall()
            
            if expired_claims:
                from src.public.core.reputation import ReputationService
                rep_service = ReputationService()
                
                for inq_id, auditor_id in expired_claims:
                    logger.warning(f"Lease Expired: Inquiry {inq_id} (Auditor: {auditor_id}). Reverting to OPEN.")
                    # Liveness Penalty (-0.1)
                    outpost = rep_service.get_outpost(auditor_id)
                    if outpost:
                        outpost.apply_liveness_event(success=False)
            
            # Revert expired claims
            conn.execute("""
                UPDATE inquiries 
                SET status = 'OPEN', claimed_by = NULL, claim_signature = NULL 
                WHERE status = 'CLAIMED' AND expires_at < ?
            """, (now,))
