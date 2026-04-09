#!/usr/bin/env python3
"""
Deep Ledger — Security & Anti-Cheat (Immune System)

Implements the Authoritative State Bridge logic to prevent Sybil attacks,
velocity abuse, and CID spoofing within the mesh.

Protections:
    - Identity Verification: All Bridge submissions must have valid Ed25519 seals.
    - Velocity Throttling: Limits submission frequency based on outpost reputation gravity.
    - Deterministic ID Friction: Validates CIDs against raw payload on ingestion.
    - Fog of War: Strips metadata for non-verified or low-REP probes.
"""

import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

from src.public.core.identity import verify_signature_with_pubkey
from src.public.core.reputation import ReputationService, ReputationTier
from src.public.core.chronicle import canonical_json

logger = logging.getLogger("security")

# ─── Security Configuration ──────────────────────────────────────

SUBMISSION_LIMITS = {
    ReputationTier.UNVERIFIED: 10, # Matches MAX_PULSES_PER_HOUR in reputation.py
    ReputationTier.SCOUT: 50,      # Matches the Tier 1+ multiplier
    ReputationTier.AUDITOR: 0,    # Unlimited for Master Auditors
}

# ─── Anti-Cheat Manager ──────────────────────────────────────────

class SecurityBridge:
    """The 'Brain' that guards the Authoritative State of the Public Chronicle."""

    def __init__(self):
        self.rep_service = ReputationService()
        self._submission_history: Dict[str, List[float]] = {}  # outpost_id -> [timestamps]

    def validate_submission(self, outpost_id: str, entry: Dict[str, Any], signature: str) -> bool:
        """
        Comprehensive validation of an incoming intelligence submission.
        
        Requirements:
            1. Outpost must be registered.
            2. Seal must be valid for the payload.
            3. Outpost must not exceed Tier-based velocity limits.
            4. CID must be deterministic (recalculatable).
        """
        # 1. Identity & Reputation Check
        outpost_rep = self.rep_service.get_outpost(outpost_id)
        if not outpost_rep:
            logger.warning(f"Submission rejected: Outpost {outpost_id} is not registered.")
            return False

        # 2. Cryptographic Integrity (ID + Data)
        # Signatures now support MultiSignature2026
        if not signature:
            proof = entry.get("proof", {})
            raw_sig = proof.get("signature") or (proof.get("signatures")[0] if proof.get("signatures") else None)
            # If it's a MultiSig object, extract the hex seal
            signature = raw_sig.get("seal") if isinstance(raw_sig, dict) else raw_sig
        # Matches logic in src.core.chronicle.create_entry/verify_entry
        signable_payload = {
            "id": entry.get("id"),
            "data": entry.get("data")
        }
        raw_signable_bytes = canonical_json(signable_payload)
        
        if not verify_signature_with_pubkey(outpost_rep.public_key_hex, raw_signable_bytes, signature):
            logger.warning(f"Submission rejected: INVALID SEAL from {outpost_id}.")
            return False

        # 3. Deterministic ID Friction
        # Recalculate CID to ensure it hasn't been spoofed
        from src.public.core.crypto import compute_cid
        try:
            cid = entry.get("id")
            data = entry.get("data")
            meta = entry.get("metadata")
            
            expected_cid = compute_cid(data, meta)
            
            if cid != expected_cid:
                logger.warning(f"Submission rejected: CID MISMATCH (Spoof attempt?). Client: {cid}, Expected: {expected_cid}")
                return False
        except Exception:
            return False

        # 4. Velocity Throttling
        if not self._check_velocity(outpost_id, outpost_rep.tier):
            logger.warning(f"Submission rejected: VELOCITY LIMIT EXCEEDED for outpost {outpost_id}.")
            return False

        return True

    def _check_velocity(self, outpost_id: str, tier: Any) -> bool:
        """Check if an outpost has exceeded its hourly submission limit."""
        # Handle both Enum and Int representations of Tier
        tier_val = tier.value if hasattr(tier, "value") else int(tier)
        limit = SUBMISSION_LIMITS.get(tier_val, SUBMISSION_LIMITS.get(tier, 1))
        
        if limit == 0: return True # Unlimited

        now = time.time()
        hour_ago = now - 3600
        
        if outpost_id not in self._submission_history:
            self._submission_history[outpost_id] = []
        
        # Clean history
        self._submission_history[outpost_id] = [t for t in self._submission_history[outpost_id] if t > hour_ago]
        
        if len(self._submission_history[outpost_id]) >= limit:
            logger.warning(f"Velocity block: {outpost_id} reached limit of {limit} pulses/hour (Tier {tier_val})")
            return False
            
        self._submission_history[outpost_id].append(now)
        return True

    def apply_fog_of_war(self, payload: Dict[str, Any], solicitor_outpost_id: str) -> Optional[Dict[str, Any]]:
        """
        Enforces tiered intelligence boundaries (Fog of War Protocol).
        
        Tiers:
            - UNVERIFIED (Tier 0): Last 24h only + Redacted metadata.
            - PROBE (Tier 1): Full history + Redacted metadata.
            - AUDITOR+ (Tier 2): Full access.
        """
        outpost_rep = self.rep_service.get_outpost(solicitor_outpost_id)
        tier = outpost_rep.tier if outpost_rep else ReputationTier.UNVERIFIED
        
        # 1. Tier 0 Boundary: Temporal Filtering (24h)
        if tier <= ReputationTier.UNVERIFIED:
            ts_str = payload.get("metadata", {}).get("timestamp")
            if ts_str:
                entry_ts = time.mktime(time.strptime(ts_str.split(".")[0], "%Y-%m-%dT%H:%M:%S"))
                if time.time() - entry_ts > 86400: # 24 hours
                    return None # Filter out old pulses for Tier 0
        
        # 2. Redaction Layer (Fog of War)
        if tier <= ReputationTier.SCOUT:
            # Strip exact source URLs and probe details for untrusted or mid-tier outposts
            redacted = payload.copy()
            if "metadata" in redacted:
                redacted["metadata"] = redacted["metadata"].copy()
                redacted["metadata"]["source_url"] = f"[REDACTED — ACCESS LEVEL {int(tier)}]"
                redacted["metadata"]["probe_id"] = "mesh-probe"
                # Tier 1 also loses evidence CIDs unless they are anchors
                if tier < ReputationTier.AUDITOR:
                    redacted["metadata"]["evidence_cid"] = "[LOCKED — ANCHOR ONLY]"
            return redacted
        
        return payload

    # ─── Hash Puzzle (Proof-of-Work) ──────────────────────────────
    
    def generate_pow_challenge(self, outpost_id: str) -> Dict[str, Any]:
        """Generates a challenge for the client to solve."""
        import secrets
        salt = secrets.token_hex(16)
        # Difficulty 5 (hex zeros) is roughly 500ms-1s on standard CPUs
        difficulty = 5 
        return {
            "salt": salt,
            "difficulty": difficulty,
            "timestamp": time.time()
        }

    def verify_hash_puzzle(self, salt: str, nonce: str, difficulty: int) -> bool:
        """Verifies the proof-of-work nonce."""
        target = "0" * difficulty
        h = hashlib.sha256(f"{salt}{nonce}".encode()).hexdigest()
        return h.startswith(target)

    def solve_hash_puzzle(self, salt: str, difficulty: int) -> str:
        """Client-side solver for the hash puzzle (for Testing/Laboratory)."""
        target = "0" * difficulty
        nonce = 0
        logger.info(f"PoW: Solving challenge (Diff: {difficulty})...")
        start = time.time()
        while True:
            h = hashlib.sha256(f"{salt}{nonce}".encode()).hexdigest()
            if h.startswith(target):
                logger.info(f"PoW: Solved in {time.time() - start:.2f}s (Nonce: {nonce})")
                return str(nonce)
            nonce += 1

# ─── Global Instance ──────────────────────────────────────────────
security_bridge = SecurityBridge()
