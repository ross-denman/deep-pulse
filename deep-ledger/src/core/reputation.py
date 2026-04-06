#!/usr/bin/env python3
"""
Deep Ledger — Reputation Service (REP-G Protocol)

Manages the Reputation-as-Gateway system. Each node's REP score determines
its access tier to the Knowledge Graph and P2P swarm resources.

This is the "Accountant" side of the Truth Economy:
- Tracks REP staking for verification bounties
- Enforces slashing when verified entries are debunked
- Manages Compute Credits earned through contribution

Tiers:
    Tier 0 (Lurker):         REP 0-99     — Rate-limited, delayed/summarized data.
    Tier 1 (Contributor):    REP 100-499  — Real-time alerts + Knowledge Graph.
    Tier 2 (Master Auditor): REP 500+     — Central Brain + consensus influence.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any

logger = logging.getLogger(__name__)


class ReputationTier(IntEnum):
    """REP-G access tiers."""

    UNVERIFIED = 0
    SCOUT = 1
    AUDITOR = 2


# Tier boundaries
TIER_THRESHOLDS = {
    ReputationTier.UNVERIFIED: (0, 99),
    ReputationTier.SCOUT: (100, 499),
    ReputationTier.AUDITOR: (500, float("inf")),
}

# REP point awards & penalties
REP_REWARDS = {
    "discovery": 5,        # Submitting a new intelligence entry
    "verification": 10,    # Successfully verifying another node's entry
    "audit_pass": 15,      # Passing an integrity audit
}

REP_PENALTIES = {
    "poison_pill": -200,    # Intentional misinformation
    "lazy_verification": -50,  # Low-effort or incorrect verification
    "spam": -25,            # Submitting duplicate or low-quality entries
    "slash": 0,             # Dynamic — calculated from staked amount
}

# Staking: percentage of current REP required to verify a claim
STAKE_PERCENTAGE = 0.10  # 10% of current REP
MIN_STAKE = 5            # Minimum stake floor

# Compute Credits: earned per verification, spent on Central Brain queries
CREDITS_PER_VERIFICATION = 3
CREDITS_PER_DISCOVERY = 1
CREDITS_PER_BRAIN_QUERY = 1


@dataclass
class ReputationEvent:
    """A single reputation change event."""

    event_type: str
    points: int
    reason: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    related_cid: str = ""
    staked_amount: int = 0  # REP staked for this verification (if applicable)


@dataclass
class NodeReputation:
    """Reputation state for a single node."""

    node_id: str
    public_key_hex: str
    score: int = 0
    compute_credits: int = 0
    active_stakes: dict[str, int] = field(default_factory=dict)  # CID -> staked REP
    history: list[ReputationEvent] = field(default_factory=list)

    @property
    def tier(self) -> ReputationTier:
        """Determine the current tier based on score."""
        if self.score >= 500:
            return ReputationTier.AUDITOR
        elif self.score >= 100:
            return ReputationTier.SCOUT
        return ReputationTier.UNVERIFIED

    @property
    def tier_name(self) -> str:
        """Human-readable tier name."""
        names = {
            ReputationTier.UNVERIFIED: "Tier 0 (Unverified)",
            ReputationTier.SCOUT: "Tier 1 (Scout/Contributor)",
            ReputationTier.AUDITOR: "Tier 2 (Master Auditor)",
        }
        return names[self.tier]

    def apply_event(self, event: ReputationEvent) -> None:
        """Apply a reputation event to this node.

        Args:
            event: The reputation change event.
        """
        old_score = self.score
        old_tier = self.tier

        self.score = max(0, self.score + event.points)  # Floor at 0
        self.history.append(event)

        new_tier = self.tier
        if new_tier != old_tier:
            logger.info(
                "Node %s tier changed: %s -> %s (score: %d -> %d)",
                self.node_id,
                old_tier.name,
                new_tier.name,
                old_score,
                self.score,
            )

    def contribution_ratio(self) -> float:
        """Calculate the Contribution-to-Consumption ratio.

        Returns:
            Ratio as a float. > 1.0 means net contributor.
        """
        contributions = sum(
            1
            for e in self.history
            if e.event_type in ("discovery", "verification", "audit_pass")
        )
        # For MVP, consumption is approximated by query count (tracked externally)
        # Here we return the raw contribution count
        return float(contributions)


class ReputationService:
    """Manages reputation scores for all known nodes.

    In MVP mode, this operates in-memory. In production,
    REP state is persisted to Neo4j with full audit trail.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, NodeReputation] = {}

    def register_node(self, node_id: str, public_key_hex: str) -> NodeReputation:
        """Register a new node with initial REP 0.

        Args:
            node_id: The Node ID.
            public_key_hex: The node's Ed25519 public key.

        Returns:
            The new NodeReputation instance.
        """
        if node_id in self._nodes:
            return self._nodes[node_id]

        rep = NodeReputation(node_id=node_id, public_key_hex=public_key_hex)
        self._nodes[node_id] = rep
        logger.info("Registered node %s at Tier 0 (REP: 0)", node_id)
        return rep

    def award(
        self,
        node_id: str,
        event_type: str,
        reason: str,
        related_cid: str = "",
    ) -> int:
        """Award reputation points to a node.

        Args:
            node_id: The node to award.
            event_type: One of the REP_REWARDS keys.
            reason: Human-readable reason.
            related_cid: Optional CID of the related Ledger entry.

        Returns:
            The node's new REP score.

        Raises:
            ValueError: If the node or event type is unknown.
        """
        node = self._nodes.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} is not registered.")

        points = REP_REWARDS.get(event_type)
        if points is None:
            raise ValueError(f"Unknown reward type: {event_type}")

        event = ReputationEvent(
            event_type=event_type,
            points=points,
            reason=reason,
            related_cid=related_cid,
        )
        node.apply_event(event)
        logger.info(
            "Awarded +%d REP to %s for '%s' (new score: %d)",
            points,
            node_id,
            reason,
            node.score,
        )
        return node.score

    def penalize(
        self,
        node_id: str,
        event_type: str,
        reason: str,
        related_cid: str = "",
    ) -> int:
        """Apply a reputation penalty to a node.

        Args:
            node_id: The node to penalize.
            event_type: One of the REP_PENALTIES keys.
            reason: Human-readable reason.
            related_cid: Optional CID of the related Ledger entry.

        Returns:
            The node's new REP score.
        """
        node = self._nodes.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} is not registered.")

        points = REP_PENALTIES.get(event_type)
        if points is None:
            raise ValueError(f"Unknown penalty type: {event_type}")

        event = ReputationEvent(
            event_type=event_type,
            points=points,
            reason=reason,
            related_cid=related_cid,
        )
        node.apply_event(event)
        logger.warning(
            "Penalized %d REP from %s for '%s' (new score: %d)",
            points,
            node_id,
            reason,
            node.score,
        )
        return node.score

    def get_node(self, node_id: str) -> NodeReputation | None:
        """Get a node's reputation state."""
        return self._nodes.get(node_id)

    def check_access(self, node_id: str, required_tier: ReputationTier) -> bool:
        """Check if a node meets the required tier for access.

        Args:
            node_id: The node to check.
            required_tier: The minimum tier required.

        Returns:
            True if the node's tier meets or exceeds the requirement.
        """
        node = self._nodes.get(node_id)
        if not node:
            return False
        return node.tier >= required_tier

    def get_leaderboard(self) -> list[tuple[str, int, str]]:
        """Get all nodes sorted by REP score descending.

        Returns:
            List of (node_id, score, tier_name) tuples.
        """
        return sorted(
            [
                (n.node_id, n.score, n.tier_name)
                for n in self._nodes.values()
            ],
            key=lambda x: x[1],
            reverse=True,
        )

    # ─── Truth Economy: Staking & Slashing ──────────────────────

    def stake_for_verification(
        self, node_id: str, entry_cid: str
    ) -> int:
        """Stake a portion of REP to verify a claim.

        The staked amount is locked until the verification outcome
        is determined. If the entry is later debunked, the stake is slashed.

        Args:
            node_id: The verifying node.
            entry_cid: The CID of the entry being verified.

        Returns:
            The amount of REP staked.

        Raises:
            ValueError: If node has insufficient REP to stake.
        """
        node = self._nodes.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} is not registered.")

        stake = max(MIN_STAKE, int(node.score * STAKE_PERCENTAGE))

        if node.score < stake:
            raise ValueError(
                f"Node {node_id} has insufficient REP ({node.score}) "
                f"to stake {stake} for verification."
            )

        node.active_stakes[entry_cid] = stake
        logger.info(
            "Node %s staked %d REP on %s (score: %d)",
            node_id, stake, entry_cid, node.score,
        )
        return stake

    def slash(
        self, node_id: str, entry_cid: str, reason: str
    ) -> int:
        """Slash a node's staked REP when a verified entry is debunked.

        Called by Master Auditors when a previously verified entry
        is proven false. The staked amount is deducted from the node's score.

        Args:
            node_id: The node to slash.
            entry_cid: The CID of the debunked entry.
            reason: Why the entry was debunked.

        Returns:
            The node's new REP score.
        """
        node = self._nodes.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} is not registered.")

        staked = node.active_stakes.pop(entry_cid, MIN_STAKE)
        slash_amount = -staked

        event = ReputationEvent(
            event_type="slash",
            points=slash_amount,
            reason=f"SLASHED: {reason}",
            related_cid=entry_cid,
            staked_amount=staked,
        )
        node.apply_event(event)
        logger.warning(
            "🔪 SLASHED %d REP from %s for debunked entry %s (new score: %d)",
            staked, node_id, entry_cid, node.score,
        )
        return node.score

    def release_stake(
        self, node_id: str, entry_cid: str
    ) -> None:
        """Release a stake after successful verification consensus.

        Called when the entry reaches 2+1 consensus and is promoted to verified.
        The staked REP is returned (not deducted).

        Args:
            node_id: The verifying node.
            entry_cid: The CID that achieved consensus.
        """
        node = self._nodes.get(node_id)
        if not node:
            return

        staked = node.active_stakes.pop(entry_cid, 0)
        if staked:
            logger.info(
                "Released %d staked REP for %s on verified entry %s",
                staked, node_id, entry_cid,
            )

    def award_compute_credits(
        self, node_id: str, event_type: str
    ) -> int:
        """Award compute credits based on contribution type.

        Credits unlock Central Brain (LLM) query quotas.

        Args:
            node_id: The contributing node.
            event_type: 'verification' or 'discovery'.

        Returns:
            The node's new compute credit balance.
        """
        node = self._nodes.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} is not registered.")

        credits = {
            "verification": CREDITS_PER_VERIFICATION,
            "discovery": CREDITS_PER_DISCOVERY,
        }.get(event_type, 0)

        node.compute_credits += credits
        logger.info(
            "Awarded +%d compute credits to %s (balance: %d)",
            credits, node_id, node.compute_credits,
        )
        return node.compute_credits

    def spend_compute_credit(
        self, node_id: str
    ) -> bool:
        """Spend one compute credit for a Central Brain query.

        Args:
            node_id: The requesting node.

        Returns:
            True if credit was available and spent, False otherwise.
        """
        node = self._nodes.get(node_id)
        if not node or node.compute_credits < CREDITS_PER_BRAIN_QUERY:
            return False

        node.compute_credits -= CREDITS_PER_BRAIN_QUERY
        return True
