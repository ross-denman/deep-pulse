#!/usr/bin/env python3
"""
The Chronicle - Consensus Manager

Implements the 2+1 Verification Triangle for promoting Public Chronicle entries
from 'speculative' to 'verified' status.

In the MVP (single outpost), this module provides the framework and stubs.
Full mesh consensus requires libp2p integration (Sprint 03).
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.identity import verify_signature_with_pubkey
from core.reputation import ReputationService

logger = logging.getLogger(__name__)


# Minimum independent verifications required (2 others + 1 originator)
CONSENSUS_THRESHOLD = 2


@dataclass
class VerificationVote:
    """A single verification vote from an outpost."""

    outpost_id: str
    public_key_hex: str
    source_path: str  # The independent source/scraping path used
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    signature: str = ""  # Signature of the CID being verified


@dataclass
class ConsensusRecord:
    """Tracks the verification state of a Public Chronicle entry."""

    entry_cid: str
    originator_outpost_id: str
    votes: list[VerificationVote] = field(default_factory=list)
    status: str = "speculative"  # speculative -> pending -> verified
    grain_inquiry: int = 0         # Locked from originator at registration

    @property
    def unique_verifiers(self) -> set[str]:
        """Return the set of unique outpost IDs that have voted."""
        return {v.outpost_id for v in self.votes}

    @property
    def independent_sources(self) -> set[str]:
        """Return the set of unique source paths used for verification."""
        return {v.source_path for v in self.votes}

    def is_consensus_reached(self) -> bool:
        """Check if the 2+1 triangulation requirement is met.

        Requirements:
        1. At least CONSENSUS_THRESHOLD independent verifications.
        2. Each verification must use a DISTINCT source path.
        3. Verifiers must be DIFFERENT outposts (no self-verification).
        """
        external_votes = [
            v for v in self.votes if v.outpost_id != self.originator_outpost_id
        ]
        unique_external_outposts = {v.outpost_id for v in external_votes}
        unique_sources = {v.source_path for v in external_votes}

        return (
            len(unique_external_outposts) >= CONSENSUS_THRESHOLD
            and len(unique_sources) >= CONSENSUS_THRESHOLD
        )


class ConsensusManager:
    """Manages the verification pipeline for Public Chronicle entries.

    In the MVP, this operates locally. In production, verification requests
    are broadcast via libp2p to mesh outposts.
    """

    def __init__(self, reputation_service: ReputationService = None) -> None:
        self._records: dict[str, ConsensusRecord] = {}
        self.reputation_service = reputation_service or ReputationService()

    def register_entry(self, entry_cid: str, originator_outpost_id: str, grain_inquiry: int = 0) -> None:
        """Register a new entry for verification tracking and lock inquiry grant."""
        if entry_cid not in self._records:
            # Enforce Economy: Spend Grains for inquiry
            if grain_inquiry > 0:
                if not self.reputation_service.spend_grains(originator_outpost_id, grain_inquiry, f"Inquiry for {entry_cid}"):
                    raise ValueError(f"Originator {originator_outpost_id} has insufficient Grains for {grain_inquiry} inquiry.")
            
            self._records[entry_cid] = ConsensusRecord(
                entry_cid=entry_cid,
                originator_outpost_id=originator_outpost_id,
                grain_inquiry=grain_inquiry
            )
            logger.info(
                "Registered entry %s for consensus tracking (originator: %s, inquiry: %d)",
                entry_cid,
                originator_outpost_id,
                grain_inquiry
            )

    def submit_vote(self, entry_cid: str, vote: VerificationVote) -> str:
        """Submit a verification vote for a Ledger entry.

        Args:
            entry_cid: The CID of the entry being verified.
            vote: The verification vote.

        Returns:
            The updated status ('speculative', 'pending_verification', 'verified').

        Raises:
            ValueError: If the entry is not registered or vote is invalid.
        """
        record = self._records.get(entry_cid)
        if not record:
            raise ValueError(f"Entry {entry_cid} is not registered for consensus.")

        # 1. Reject self-verification
        if vote.outpost_id == record.originator_outpost_id:
            raise ValueError("Self-verification is not allowed (Zero-Trust rule).")

        # 2. Reject duplicate votes from the same outpost
        if vote.outpost_id in record.unique_verifiers:
            raise ValueError(f"Outpost {vote.outpost_id} has already voted on {entry_cid}.")

        # 3. Economy: Staking Requirement
        # Before submitting a vote, the outpost must STAKE their own REP.
        self.reputation_service.stake_for_verification(vote.outpost_id, entry_cid)

        record.votes.append(vote)
        logger.info(
            "Vote recorded for %s from outpost %s (source: %s)",
            entry_cid,
            vote.outpost_id,
            vote.source_path,
        )

        # 4. Check consensus
        if record.is_consensus_reached():
            record.status = "verified"
            logger.info("[OK] Consensus reached for %s - promoted to VERIFIED", entry_cid)
            
            # Payout Grain Inquiries (Economy: The Metabolism)
            if record.grain_inquiry > 0:
                reward_per_node = record.grain_inquiry // len(record.votes)
                for v_id in record.unique_verifiers:
                    self.reputation_service.award_grains(v_id, reward_per_node, f"Inquiry payout for {entry_cid}")
                    self.reputation_service.release_stake(v_id, entry_cid)
                    # Reward REP as well
                    self.reputation_service.award(v_id, "verification", f"Consensus Verification for {entry_cid}")
        
        elif len(record.votes) > 0:
            record.status = "pending_verification"

        return record.status

    def get_status(self, entry_cid: str) -> str:
        """Get the current verification status of an entry.

        Args:
            entry_cid: The CID to query.

        Returns:
            Status string.
        """
        record = self._records.get(entry_cid)
        return record.status if record else "unknown"

    def get_record(self, entry_cid: str) -> ConsensusRecord | None:
        """Get the full consensus record for an entry.

        Args:
            entry_cid: The CID to query.

        Returns:
            The ConsensusRecord or None.
        """
        return self._records.get(entry_cid)
