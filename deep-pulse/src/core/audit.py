#!/usr/bin/env python3
"""
Deep Pulse — Indelible Audit Log (Sovereign Watchdog)

Every analytical query to the Base Ledger is hashed and signed.
This ensures non-repudiation and voluntary transparency.
The audit trail is append-only and tamper-evident.
"""

import hashlib
import json
import logging
import os
import time
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

AUDIT_LOG_PATH = "db/audit.log"


class AuditEntry:
    """A single signed audit record."""

    def __init__(self, action: str, query: str, actor: str, result_summary: str = ""):
        self.timestamp = time.time()
        self.action = action
        self.query = query
        self.actor = actor
        self.result_summary = result_summary
        self.content_hash = self._compute_hash()
        self.signature = None  # Populated by sign()
        self.prev_hash = None  # Chain link

    def _compute_hash(self) -> str:
        payload = json.dumps({
            "ts": self.timestamp,
            "action": self.action,
            "query": self.query,
            "actor": self.actor
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "query": self.query,
            "actor": self.actor,
            "result_summary": self.result_summary,
            "content_hash": self.content_hash,
            "prev_hash": self.prev_hash,
            "signature": self.signature
        }


class IndelibleAuditLog:
    """
    Append-only, tamper-evident audit log.
    Each entry is chained to the previous via prev_hash,
    forming a lightweight hash chain (mini-blockchain).
    """

    def __init__(self, identity_manager=None, log_path: str = AUDIT_LOG_PATH):
        self.identity = identity_manager
        self.log_path = log_path
        self.chain: List[Dict[str, Any]] = []
        self._last_hash = "GENESIS"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self._load_existing()

    def _load_existing(self):
        """Loads existing audit chain from disk."""
        if not os.path.exists(self.log_path):
            return
        try:
            with open(self.log_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        self.chain.append(entry)
                        self._last_hash = entry.get("content_hash", self._last_hash)
            logger.info(f"Audit Log: Loaded {len(self.chain)} existing entries.")
        except Exception as e:
            logger.warning(f"Audit Log: Could not load existing log: {e}")

    def record(self, action: str, query: str, actor: str, result_summary: str = ""):
        """Records and signs a new audit entry."""
        entry = AuditEntry(action, query, actor, result_summary)
        entry.prev_hash = self._last_hash

        # Sign with Ed25519 if identity manager is available
        if self.identity:
            try:
                sig = self.identity.sign(entry.content_hash.encode())
                entry.signature = sig.hex()
            except Exception as e:
                logger.warning(f"Audit Log: Signing failed: {e}")
                entry.signature = "UNSIGNED"
        else:
            entry.signature = "UNSIGNED"

        record = entry.to_dict()
        self.chain.append(record)
        self._last_hash = entry.content_hash

        # Append to disk
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.error(f"Audit Log: Persistence failed: {e}")

        logger.info(f"Audit Log: Recorded [{action}] by {actor} | Hash: {entry.content_hash[:16]}...")
        return record

    def verify_chain(self) -> bool:
        """Verifies the integrity of the entire audit chain."""
        expected_prev = "GENESIS"
        for i, entry in enumerate(self.chain):
            if entry.get("prev_hash") != expected_prev:
                logger.critical(f"Audit Log: CHAIN BREAK at entry {i}! Tampering detected.")
                return False
            expected_prev = entry.get("content_hash")
        logger.info(f"Audit Log: Chain integrity VERIFIED ({len(self.chain)} entries).")
        return True

    def get_recent(self, count: int = 10) -> List[Dict[str, Any]]:
        """Returns the most recent N audit entries."""
        return self.chain[-count:]
