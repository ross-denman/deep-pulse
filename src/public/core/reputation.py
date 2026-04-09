"""
The Chronicle — Reputation Service (REP-G Protocol)

Manages the Reputation-as-Gateway system. Each Probe's REP score determines
its access tier to the Knowledge Graph and mesh resources.

This is the "Accountant" side of the Truth Economy:
- Tracks Grains staking for verification inquiries
- Enforces Grains Slashing when verified entries are debunked
- Manages Grains earned through settling and discovery

Tiers:
    Tier 0 (Lurker):         REP 0-99     — Rate-limited, delayed/summarized data.
    Tier 1 (Probe):          REP 100-499  — Real-time alerts + Knowledge Graph.
    Tier 2 (Auditor):         REP 500+     — Central Brain + consensus influence.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json

# Resolve to soul-ledger root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
REPUTATION_FILE = PROJECT_ROOT / "harvest" / "reputation.json"
SOVEREIGN_TREASURY_ID = "TREASURY"

logger = logging.getLogger(__name__)


class ReputationTier(IntEnum):
    """REP-G access tiers."""

    UNVERIFIED = 0
    SCOUT = 1
    AUDITOR = 2
    SOVEREIGN_NOTARY = 3

    @property
    def voting_weight(self) -> float:
        """Voting weight for Multi-Sig consensus."""
        weights = {
            ReputationTier.UNVERIFIED: 0.0,
            ReputationTier.SCOUT: 0.1,
            ReputationTier.AUDITOR: 0.5,
            ReputationTier.SOVEREIGN_NOTARY: 1.0,
        }
        return weights.get(self, 0.0)


# Tier boundaries (Updated for Sprint 16 Sandbox)
TIER_THRESHOLDS = {
    ReputationTier.UNVERIFIED: (0.0, 0.99),
    ReputationTier.SCOUT: (1.0, 4.99), # Rebranded or transitional
    ReputationTier.AUDITOR: (5.0, 19.99), # We'll keep Auditor at 1.0 for the user's specific request
    ReputationTier.SOVEREIGN_NOTARY: (20.0, float("inf")),
}

# REP point awards & penalties
REP_REWARDS = {
    "discovery": 5,        # Submitting a new intelligence entry
    "verification": 10,    # Successfully verifying another Probe's entry
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

# Velocity Limits (Anti-Cheat)
MAX_PULSES_PER_HOUR = 10 # Hard limit for Tier 0
VELOCITY_WINDOW_SECONDS = 3600

# Grains Economy
GRAIN_YIELD_BASE = 5         # Base Grains per day for Tier 0
GRAIN_YIELD_PER_100_REP = 10 
GRAIN_COST_SYNC = 1          
GRAIN_MIN_INQUIRY = 2         

# Phase 3: Dynamic Weighting
SUBMISSION_WEIGHT = 10
ATTESTATION_WEIGHT = 5
SLASH_PENALTY = 100
BIRTH_REP = 50  # Starting base score if Genesis found

# Phase 5: Liveness Metric
LIVENESS_PENALTY = 0.1
LIVENESS_RECOVERY = 0.05
LIVENESS_THRESHOLD = 0.85 # Minimum liveness for high-gravity bounties


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
class SourceReputation:
    """Reputation state for a data source (URL)."""
    source_url: str
    sr_g: float = 0.0
    status: str = "SPECULATIVE"
    verified_count: int = 0
    total_count: int = 0

    @property
    def trust_score(self) -> float:
        """Normalized trust score for a source (0.0 - 1.0)."""
        if self.total_count == 0: return 0.0
        return round(self.verified_count / self.total_count, 3)

    @property
    def multiplier(self) -> float:
        """Calculate the Sovereign Multiplier for this source."""
        from src.public.core.sources import source_validator
        return source_validator.get_multiplier(self.source_url)


@dataclass
class OutpostReputation:
    """Reputation state for a single outpost."""

    outpost_id: str
    public_key_hex: str
    score: float = 0.0
    grain_balance: int = 25  # Starting "Grains" liquidity
    last_yield_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    active_stakes: dict[str, int] = field(default_factory=dict)  # CID -> staked REP
    active_inquiries: dict[str, int] = field(default_factory=dict) # CID -> Grains inquiry
    liveness_score: float = 1.0  # Phase 5: Auditor Liveness (0.0 - 1.0)
    history: list[ReputationEvent] = field(default_factory=list)

    @property
    def tier(self) -> ReputationTier:
        """Determine the current tier based on score."""
        # Sprint 16: Simplified Sandbox Tiers
        if self.score >= 20.0:
            return ReputationTier.SOVEREIGN_NOTARY
        elif self.score >= 1.0:
            return ReputationTier.AUDITOR
        elif self.score >= 0.5:
            return ReputationTier.SCOUT
        return ReputationTier.UNVERIFIED

    @property
    def tier_name(self) -> str:
        """Human-readable tier name."""
        names = {
            ReputationTier.UNVERIFIED: "Tier 0 (Unverified)",
            ReputationTier.SCOUT: "Tier 1 (Probe/Contributor)",
            ReputationTier.AUDITOR: "Tier 2 (Auditor)",
            ReputationTier.SOVEREIGN_NOTARY: "Tier 3 (Sovereign Notary)",
        }
        return names[self.tier]

    @property
    def trust_score(self) -> float:
        """Calculate a deterministic math-based trust score (0.0 - 1.0)."""
        if self.score <= 0: return 0.0
        pivot = 500
        return round(self.score / (self.score + pivot), 3)

    def calculate_ledger_reputation(self, ledger: List[Dict[str, Any]]) -> float:
        """Derive score from **The Chronicle** scanning (Phase 3)."""
        score = 0.0
        now = datetime.now(timezone.utc)
        
        has_genesis = False
        
        for entry in ledger:
            if entry.get("id") == "chronicle:genesis":
                # Check if this outpost is the one initialized in genesis
                # (Or if they have a genesis entry in their history)
                if entry.get("metadata", {}).get("outpost_id") == self.outpost_id:
                    has_genesis = True
                continue

            # 1. Submission Check (Originator)
            meta = entry.get("metadata", {})
            if meta.get("outpost_id") == self.outpost_id:
                if meta.get("status") == "verified":
                    score += SUBMISSION_WEIGHT * self._get_decay_factor(meta.get("timestamp"), now)

            # 2. Attestation Check (Signer)
            signatures = entry.get("proof", {}).get("signatures", [])
            for sig in signatures:
                if sig.get("outpost_id") == self.outpost_id:
                    # Don't count self-signing your own submission as an attestation
                    if meta.get("outpost_id") != self.outpost_id:
                        if meta.get("status") == "verified":
                            score += ATTESTATION_WEIGHT * self._get_decay_factor(sig.get("timestamp"), now)

            # 3. Slashing Check
            if entry.get("data", {}).get("type") == "ReputationSlash":
                if entry.get("data", {}).get("target_outpost_id") == self.outpost_id:
                    score -= SLASH_PENALTY

        if has_genesis:
            score += BIRTH_REP

        return round(max(0.0, score), 2)

    def _get_decay_factor(self, timestamp_str: Optional[str], now: datetime) -> float:
        """Calculate time decay: 1.0 (<30d), 0.5 (30-90d), 0.1 (>90d)."""
        if not timestamp_str:
            return 1.0
        try:
            ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            days_old = (now - ts).days
            if days_old < 30:
                return 1.0
            elif days_old < 90:
                return 0.5
            else:
                return 0.1
        except Exception:
            return 1.0

    def apply_event(self, event: ReputationEvent) -> None:
        """Apply a reputation event to this outpost."""
        old_score = self.score
        old_tier = self.tier

        self.score = round(self.score + event.points, 4) # We allow negative drift but floor at logic
        
        # Demotion Logic: If score falls below hard thresholds, tier drops automatically.
        # This is handled by the @property tier naturally.
        
        self.history.append(event)

        new_tier = self.tier
        if new_tier != old_tier:
            logger.info(
                "Outpost %s tier changed: %s -> %s (score: %.2f -> %.2f)",
                self.outpost_id,
                old_tier.name,
                new_tier.name,
                old_score,
                self.score,
            )

    def apply_liveness_event(self, success: bool) -> float:
        """Update liveness score based on audit performance.
        
        Args:
            success: True if an inquiry was completed on time, False if it expired.
        """
        if success:
            # Slow recovery
            self.liveness_score = min(1.0, self.liveness_score + LIVENESS_RECOVERY)
        else:
            # Sharp penalty
            self.liveness_score = max(0.0, self.liveness_score - LIVENESS_PENALTY)
        
        logger.info("Outpost %s liveness updated: %.2f (Success: %s)", 
                    self.outpost_id, self.liveness_score, success)
        return self.liveness_score

    def calculate_daily_yield(self) -> int:
        """Calculate the daily 'Grains' yield based on Grains of Truth score."""
        bonus = (self.score // 100) * GRAIN_YIELD_PER_100_REP
        return GRAIN_YIELD_BASE + bonus

    def apply_daily_yield(self) -> int:
        """Apply the Grain yield since the last update."""
        now = datetime.now(timezone.utc)
        last = datetime.fromisoformat(self.last_yield_timestamp)
        
        days_passed = (now - last).days
        if days_passed > 0:
            yield_total = days_passed * self.calculate_daily_yield()
            self.grain_balance += yield_total
            self.last_yield_timestamp = now.isoformat()
            logger.info("Outpost %s generated %d Grains yield.", self.outpost_id, yield_total)
            return yield_total
        return 0

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
    """Manages reputation scores for all known Probes.

    In MVP mode, this operates in-memory with optional caching.
    State is derived from **The Chronicle** (Phase 3).
    """

    def __init__(self) -> None:
        self._outposts: dict[str, OutpostReputation] = {}
        self._sources: dict[str, SourceReputation] = {}
        self._last_ledger_hash: str = ""
        self.load_state()

    def refresh_if_dirty(self, ledger: List[Dict[str, Any]]) -> None:
        """Invalidate and refresh cache if the ledger has changed (Phase 3)."""
        if not ledger:
            return
            
        current_hash = ledger[-1].get("id", "")
        if current_hash != self._last_ledger_hash:
            logger.info("Ledger change detected. Refreshing reputation cache...")
            self._recalculate_outposts(ledger)
            self._recalculate_sources(ledger)
            self._last_ledger_hash = current_hash
            self.save_state()

    def _recalculate_outposts(self, ledger: List[Dict[str, Any]]) -> None:
        """Full rebuild of Probe scores from the ledger."""
        for outpost in self._outposts.values():
            new_score = outpost.calculate_ledger_reputation(ledger)
            outpost.score = int(new_score)
        logger.info(f"Rebuilt scores for {len(self._outposts)} Probes.")

    def _recalculate_sources(self, ledger: List[Dict[str, Any]]) -> None:
        """Full rebuild of source reputation ($SR-G) from the ledger."""
        source_data: Dict[str, Dict[str, Any]] = {}

        for entry in ledger:
            if entry.get("id") == "chronicle:genesis": continue
            
            meta = entry.get("metadata", {})
            source_url = meta.get("source_url")
            if not source_url: continue

            if source_url not in source_data:
                source_data[source_url] = {"verified_count": 0, "total_count": 0}

            source_data[source_url]["total_count"] += 1
            if meta.get("status") == "verified":
                source_data[source_url]["verified_count"] += 1

        for url, stats in source_data.items():
            sr_g = stats["verified_count"] * 10.0
            status = "SPECULATIVE"
            if stats["verified_count"] >= 25:
                status = "VERIFIED"
            elif stats["verified_count"] >= 10:
                status = "PROBATIONARY"

            self._sources[url] = SourceReputation(
                source_url=url,
                sr_g=sr_g,
                status=status,
                verified_count=stats["verified_count"],
                total_count=stats["total_count"]
            )
        logger.info(f"Rebuilt $SR-G for {len(self._sources)} sources from ledger.")

    def load_state(self) -> None:
        """Load reputation state from harvest/reputation.json."""
        if not REPUTATION_FILE.exists():
            self._genesis_mint()
            return
        
        try:
            with open(REPUTATION_FILE, "r") as f:
                data = json.load(f)
                
                # Load Outposts
                outposts_data = data.get("outposts", {})
                for outpost_id, o_data in outposts_data.items():
                    outpost = OutpostReputation(
                        outpost_id=outpost_id,
                        public_key_hex=o_data.get("public_key_hex"),
                        score=o_data.get("score", 0),
                        grain_balance=o_data.get("grain_balance", 25),
                        liveness_score=o_data.get("liveness_score", 1.0)
                    )
                    self._outposts[outpost_id] = outpost
                
                # Load Sources
                sources_data = data.get("sources", {})
                for url, s_data in sources_data.items():
                    self._sources[url] = SourceReputation(
                        source_url=url,
                        sr_g=s_data.get("sr_g", 0.0),
                        status=s_data.get("status", "SPECULATIVE"),
                        verified_count=s_data.get("verified_count", 0),
                        total_count=s_data.get("total_count", 0)
                    )
                    
            if SOVEREIGN_TREASURY_ID not in self._outposts:
                self._genesis_mint()
            else:
                logger.info("Reputation state restored from %s", REPUTATION_FILE)
        except Exception as e:
            logger.error("Failed to load reputation state: %s", e)

    def _genesis_mint(self) -> None:
        """Initializes the Sovereign Treasury with bootstrap liquidity."""
        logger.info("Initializing Sovereign Treasury (Genesis Mint: 25,000 Grains)")
        # The Treasury is a Tier 3 identity by default
        treasury = OutpostReputation(
            outpost_id=SOVEREIGN_TREASURY_ID,
            public_key_hex="SYSTEM",
            score=2000,
            grain_balance=25000,
            liveness_score=1.0
        )
        self._outposts[SOVEREIGN_TREASURY_ID] = treasury
        self.save_state()

    def save_state(self) -> None:
        """Save current reputation state to harvest/reputation.json."""
        REPUTATION_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = {
                "outposts": {
                    outpost_id: {
                        "public_key_hex": outpost.public_key_hex,
                        "score": outpost.score,
                        "grain_balance": outpost.grain_balance,
                        "liveness_score": outpost.liveness_score,
                        "tier": int(outpost.tier)
                    }
                    for outpost_id, outpost in self._outposts.items()
                },
                "sources": {
                    url: {
                        "sr_g": src.sr_g,
                        "status": src.status,
                        "verified_count": src.verified_count,
                        "total_count": src.total_count
                    }
                    for url, src in self._sources.items()
                }
            }
            with open(REPUTATION_FILE, "w") as f:
                json.dump(data, f, indent=2)
            logger.info("Reputation state saved to %s", REPUTATION_FILE)
        except Exception as e:
            logger.error("Failed to save reputation state: %s", e)

    def register_outpost(self, outpost_id: str, public_key_hex: str) -> OutpostReputation:
        """Register a new outpost with initial REP 0.

        Args:
            outpost_id: The Outpost ID.
            public_key_hex: The outpost's Ed25519 public key.

        Returns:
            The new OutpostReputation instance.
        """
        if outpost_id in self._outposts:
            return self._outposts[outpost_id]

        rep = OutpostReputation(outpost_id=outpost_id, public_key_hex=public_key_hex)
        self._outposts[outpost_id] = rep
        logger.info("Registered outpost %s at Tier 0 (REP: 0)", outpost_id)
        self.save_state()
        return rep

    def award(
        self,
        outpost_id: str,
        event_type: str,
        reason: str,
        related_cid: str = "",
        points: int = None
    ) -> int:
        """Award reputation points to an outpost."""
        outpost = self._outposts.get(outpost_id)
        if not outpost:
            raise ValueError(f"Outpost {outpost_id} is not registered.")

        pts = points if points is not None else REP_REWARDS.get(event_type)
        if pts is None:
            raise ValueError(f"Unknown reward type: {event_type}")

        event = ReputationEvent(
            event_type=event_type,
            points=pts,
            reason=reason,
            related_cid=related_cid,
        )
        outpost.apply_event(event)
        
        logger.info(
            "Awarded +%d REP to %s for '%s' (new score: %d)",
            pts,
            outpost_id,
            reason,
            outpost.score,
        )
        self.save_state()
        return outpost.score

    def apply_anomaly_penalty(
        self,
        outpost_id: str,
        reason: str,
        severity: str = "LOW",
        related_cid: str = "",
    ) -> int:
        """Apply a reputation penalty for noise or anomalies.
        
        Uses a decaying/exponential pattern: 
        1st strike: Warning
        2nd+: base * (2 ^ strikes)
        """
        outpost = self._outposts.get(outpost_id)
        if not outpost:
            raise ValueError(f"Outpost {outpost_id} is not registered.")

        # Calculate penalty based on history
        recent_anomalies = [e for e in outpost.history if "ANOMALY" in e.reason or "NOISE" in e.reason]
        strike_count = len(recent_anomalies)

        base_penalties = {
            "LOW": 5,
            "MEDIUM": 25,
            "HIGH": 100,
            "CRITICAL": 250
        }
        base = base_penalties.get(severity, 5)
        
        # Exponential escalation
        penalty_val = base * (2 ** strike_count)
        points = -penalty_val

        event = ReputationEvent(
            event_type="spam" if severity == "LOW" else "slash",
            points=points,
            reason=f"ANOMALY ({severity}): {reason}",
            related_cid=related_cid,
        )
        outpost.apply_event(event)

        logger.warning(
            "🛑 NOISE PENALTY: %d REP from %s for '%s' (Strike %d)",
            points, outpost_id, reason, strike_count + 1
        )
        return outpost.score

    def is_outpost_silenced(self, outpost_id: str) -> bool:
        """Check if an outpost is relegated to Tier 0 (Low Priority Silence)."""
        outpost = self._outposts.get(outpost_id)
        if not outpost:
            return True
        return outpost.tier == ReputationTier.UNVERIFIED

    def check_velocity(self, outpost_id: str) -> bool:
        """Sovereign Notary Anti-Cheat: Measures submission frequency.
        
        Returns False if the outpost has exceeded its velocity threshold.
        """
        outpost = self._outposts.get(outpost_id)
        if not outpost:
            return False

        # Tier 1+ outposts have higher velocity limits
        limit = MAX_PULSES_PER_HOUR if outpost.tier == ReputationTier.UNVERIFIED else MAX_PULSES_PER_HOUR * 5
        
        now = datetime.now(timezone.utc)
        one_hour_ago = now.timestamp() - VELOCITY_WINDOW_SECONDS
        
        recent_pulses = [
            e for e in outpost.history 
            if e.event_type == "discovery" and datetime.fromisoformat(e.timestamp).timestamp() > one_hour_ago
        ]
        
        if len(recent_pulses) >= limit:
            logger.warning("Velocity Spike detected for outpost %s. Throttling.", outpost_id)
            return False
            
        return True

    def get_source(self, url: str) -> SourceReputation:
        """Get or initialize reputation for a data source."""
        return self._sources.get(url, SourceReputation(source_url=url))

    def get_outpost(self, outpost_id: str) -> OutpostReputation | None:
        """Get an outpost's reputation state."""
        return self._outposts.get(outpost_id)

    def check_access(self, outpost_id: str, required_tier: ReputationTier) -> bool:
        """Check if an outpost meets the required tier for access.

        Args:
            outpost_id: The outpost to check.
            required_tier: The minimum tier required.

        Returns:
            True if the outpost's tier meets or exceeds the requirement.
        """
        outpost = self._outposts.get(outpost_id)
        if not outpost:
            return False
        return outpost.tier >= required_tier

    def apply_yield_to_all(self) -> dict[str, int]:
        """Apply daily Grains yield and Forgiveness Decay to all registered outposts."""
        results = {}
        for outpost_id, outpost in self._outposts.items():
            # 1. Grain Yield
            yield_pts = outpost.apply_daily_yield()
            if yield_pts > 0:
                results[outpost_id] = yield_pts
            
            # 2. Forgiveness Decay (Negative Recovery)
            # If reputation is negative, it drifts back toward 0.0 (+0.01/day)
            if outpost.score < 0:
                outpost.score = min(0.0, round(outpost.score + 0.01, 4))
                logger.info(f"Outpost {outpost_id} Reputation Forgiveness Decay: {outpost.score}")
                
        return results

    def get_leaderboard(self) -> list[tuple[str, int, str]]:
        """Get all outposts sorted by REP score descending.

        Returns:
            List of (outpost_id, score, tier_name) tuples.
        """
        return sorted(
            [
                (n.outpost_id, n.score, n.tier_name)
                for n in self._outposts.values()
            ],
            key=lambda x: x[1],
            reverse=True,
        )

    # ─── Truth Economy: Staking & Slashing ──────────────────────

    def stake_for_verification(
        self, outpost_id: str, entry_cid: str
    ) -> int:
        """Stake a portion of REP to verify a claim.

        The staked amount is locked until the verification outcome
        is determined. If the entry is later debunked, the stake is slashed.

        Args:
            outpost_id: The verifying outpost.
            entry_cid: The CID of the entry being verified.

        Returns:
            The amount of REP staked.

        Raises:
            ValueError: If outpost has insufficient REP to stake.
        """
        outpost = self._outposts.get(outpost_id)
        if not outpost:
            raise ValueError(f"Outpost {outpost_id} is not registered.")

        stake = max(MIN_STAKE, int(outpost.score * STAKE_PERCENTAGE))

        if outpost.score < stake:
            raise ValueError(
                f"Outpost {outpost_id} has insufficient REP ({outpost.score}) "
                f"to stake {stake} for verification."
            )

        outpost.active_stakes[entry_cid] = stake
        logger.info(
            "Outpost %s staked %d REP on %s (score: %d)",
            outpost_id, stake, entry_cid, outpost.score,
        )
        return stake

    def slash(
        self, outpost_id: str, entry_cid: str, reason: str
    ) -> int:
        """Slash an outpost's staked REP when a verified entry is debunked.

        Called by Master Auditors when a previously verified entry
        is proven false. The staked amount is deducted from the outpost's score.

        Args:
            outpost_id: The outpost to slash.
            entry_cid: The CID of the debunked entry.
            reason: Why the entry was debunked.

        Returns:
            The outpost's new REP score.
        """
        outpost = self._outposts.get(outpost_id)
        if not outpost:
            raise ValueError(f"Outpost {outpost_id} is not registered.")

        staked = outpost.active_stakes.pop(entry_cid, MIN_STAKE)
        slash_amount = -staked

        event = ReputationEvent(
            event_type="slash",
            points=slash_amount,
            reason=f"SLASHED: {reason}",
            related_cid=entry_cid,
            staked_amount=staked,
        )
        outpost.apply_event(event)
        logger.warning(
            "🔪 SLASHED %d REP from %s for debunked entry %s (new score: %d)",
            staked, outpost_id, entry_cid, outpost.score,
        )
        return outpost.score

    def release_stake(
        self, outpost_id: str, entry_cid: str
    ) -> None:
        """Release a stake after successful verification consensus.

        Called when the entry reaches 2+1 consensus and is promoted to verified.
        The staked REP is returned (not deducted).

        Args:
            outpost_id: The verifying outpost.
            entry_cid: The CID that achieved consensus.
        """
        outpost = self._outposts.get(outpost_id)
        if not outpost:
            return

        staked = outpost.active_stakes.pop(entry_cid, 0)
        if staked:
            logger.info(
                "Released %d staked REP for %s on verified entry %s",
                staked, outpost_id, entry_cid,
            )

    def award_grains(
        self, outpost_id: str, amount: int, reason: str
    ) -> int:
        """Award Grains to an outpost for contributions (discoveries, verification)."""
        outpost = self._outposts.get(outpost_id)
        if not outpost:
            raise ValueError(f"Outpost {outpost_id} is not registered.")

        outpost.grain_balance += amount
        logger.info(
            "Awarded +%d Grains to %s for '%s' (balance: %d)",
            amount, outpost_id, reason, outpost.grain_balance,
        )
        self.save_state()
        return outpost.grain_balance

    def spend_grains(
        self, outpost_id: str, amount: int, reason: str
    ) -> bool:
        """Spend Grains for syncing or queries."""
        outpost = self._outposts.get(outpost_id)
        if not outpost or outpost.grain_balance < amount:
            return False

        outpost.grain_balance -= amount
        logger.info(
            "Outpost %s spent %d Grains: %s (balance: %d)",
            outpost_id, amount, reason, outpost.grain_balance
        )
        self.save_state()
        return True

    def post_grain_inquiry(
        self, outpost_id: str, entry_cid: str, amount: int
    ) -> int:
        """Post a Grains inquiry to incentivize verification of a discovery."""
        outpost = self._outposts.get(outpost_id)
        if not outpost or outpost.grain_balance < amount or amount < GRAIN_MIN_INQUIRY:
            raise ValueError("Insufficient Grain balance or below minimum inquiry.")

        outpost.grain_balance -= amount
        outpost.active_inquiries[entry_cid] = amount
        logger.info(
            "Outpost %s posted %d Grains inquiry on %s.",
            outpost_id, amount, entry_cid
        )
        return amount
