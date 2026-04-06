#!/usr/bin/env python3
"""
Deep Ledger — Consensus Manager

Implements the 2+1 Verification Triangle for promoting Ledger entries
from 'speculative' to 'verified' status.

In the MVP (single node), this module provides the framework and stubs.
Full P2P consensus requires libp2p integration (Sprint 03).
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.core.identity import verify_signature_with_pubkey

logger = logging.getLogger(__name__)


# Minimum independent verifications required (2 others + 1 originator)
CONSENSUS_THRESHOLD = 2


@dataclass
class VerificationVote:
    """A single verification vote from a node."""

    node_id: str
    public_key_hex: str
    source_path: str  # The independent source/scraping path used
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    signature: str = ""  # Signature of the CID being verified


@dataclass
class ConsensusRecord:
    """Tracks the verification state of a Ledger entry."""

    entry_cid: str
    originator_node_id: str
    votes: list[VerificationVote] = field(default_factory=list)
    status: str = "speculative"  # speculative -> pending -> verified

    @property
    def unique_verifiers(self) -> set[str]:
        """Return the set of unique node IDs that have voted."""
        return {v.node_id for v in self.votes}

    @property
    def independent_sources(self) -> set[str]:
        """Return the set of unique source paths used for verification."""
        return {v.source_path for v in self.votes}

    def is_consensus_reached(self) -> bool:
        """Check if the 2+1 triangulation requirement is met.

        Requirements:
        1. At least CONSENSUS_THRESHOLD independent verifications.
        2. Each verification must use a DISTINCT source path.
        3. Verifiers must be DIFFERENT nodes (no self-verification).
        """
        external_votes = [
            v for v in self.votes if v.node_id != self.originator_node_id
        ]
        unique_external_nodes = {v.node_id for v in external_votes}
        unique_sources = {v.source_path for v in external_votes}

        return (
            len(unique_external_nodes) >= CONSENSUS_THRESHOLD
            and len(unique_sources) >= CONSENSUS_THRESHOLD
        )


class ConsensusManager:
    """Manages the verification pipeline for Ledger entries.

    In the MVP, this operates locally. In production, verification requests
    are broadcast via libp2p to peer nodes.
    """

    def __init__(self) -> None:
        self._records: dict[str, ConsensusRecord] = {}

    def register_entry(self, entry_cid: str, originator_node_id: str) -> None:
        """Register a new entry for verification tracking.

        Args:
            entry_cid: The CID of the Ledger entry.
            originator_node_id: The Node ID of the entry's creator.
        """
        if entry_cid not in self._records:
            self._records[entry_cid] = ConsensusRecord(
                entry_cid=entry_cid,
                originator_node_id=originator_node_id,
            )
            logger.info(
                "Registered entry %s for consensus tracking (originator: %s)",
                entry_cid,
                originator_node_id,
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

        # Reject self-verification
        if vote.node_id == record.originator_node_id:
            raise ValueError("Self-verification is not allowed (Zero-Trust rule).")

        # Reject duplicate votes from the same node
        if vote.node_id in record.unique_verifiers:
            raise ValueError(f"Node {vote.node_id} has already voted on {entry_cid}.")

        record.votes.append(vote)
        logger.info(
            "Vote recorded for %s from node %s (source: %s)",
            entry_cid,
            vote.node_id,
            vote.source_path,
        )

        # Check consensus
        if record.is_consensus_reached():
            record.status = "verified"
            logger.info("✅ Consensus reached for %s — promoted to VERIFIED", entry_cid)
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
