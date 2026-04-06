#!/usr/bin/env python3
"""
Deep Pulse — Economy Service (Truth Economy Engine)

Manages the reputation-based economic incentives for the swarm.
No cryptocurrency — instead, verification bounties, REP staking,
and Compute Credits.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Economic Constants
STAKE_PERCENTAGE = 0.10  # 10% of current REP-G
MIN_STAKE = 5            # Minimum stake floor
CREDITS_PER_VERIFICATION = 3
REP_G_AWARD_PER_VERIFICATION = 1 # Earnings for successfully verifying pulse
CREDITS_PER_DISCOVERY = 1
CREDITS_PER_BRAIN_QUERY = 1

class TruthEconomyManager:
    """Manages REP-G (Reputation-Gossip), verification bounties, and compute credits."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.rep_g = 0 # Reputation-Gossip (earned weight)
        self.compute_credits = 10 # Genesis Grant minted for 2026 Audit
        self.active_stakes = {}  # CID -> staked REP-G amount

    def update_rep_score(self, new_score: int):
        """Updates the local node's cached REP-G score from the Ledger."""
        self.rep_g = new_score

    def calculate_stake(self, claim_tier: int = 1) -> int:
        """
        Calculates the required REP-G stake for a verification audit.
        Tier-based Stake Slicing: Higher-tier claims require more REP-G.
        """
        # Sybil Resistance: A "new" node has zero REP-G and cannot influence consensus.
        # They must first earn REP-G before being able to stake/verify meaningfully.
        if self.rep_g < MIN_STAKE:
             return MIN_STAKE 
             
        base_stake = max(MIN_STAKE, int(self.rep_g * STAKE_PERCENTAGE))
        
        # Stake Slicing modifier
        # Tier 0 (Normal): 1x
        # Tier 1 (High): 2x
        # Tier 2 (Critical): 5x
        modifiers = {0: 1, 1: 2, 2: 5}
        multiplier = modifiers.get(claim_tier, 1)
        
        return base_stake * multiplier

    def stake_for_audit(self, cid: str, claim_tier: int = 0) -> bool:
        """Locks REP-G to verify a claim."""
        stake_amount = self.calculate_stake(claim_tier)
        
        if self.rep_g < stake_amount:
            logger.warning(f"Insufficient REP-G ({self.rep_g}) to stake {stake_amount} for {cid}")
            return False
            
        self.active_stakes[cid] = stake_amount
        logger.info(f"Staked {stake_amount} REP-G on verification audit for {cid}")
        return True

    def slash_on_debunk(self, cid: str) -> int:
        """Slashes the staked REP-G if the verification is debunked."""
        staked_amount = self.active_stakes.pop(cid, MIN_STAKE)
        # Slicing Penalty: Lying about "High-Tier" intel incurs 2x standard slash
        # (Already captured in the staked amount being higher)
        self.rep_g = max(0, self.rep_g - staked_amount)
        logger.warning(f"SLASHED! Removed {staked_amount} REP-G for debunked entry {cid}")
        return self.rep_g

    def reward_on_consensus(self, cid: str, event_type: str = "verification"):
        """Releases stake and awards compute credits and REP-G."""
        staked = self.active_stakes.pop(cid, 0)
        
        rewards = {
            "verification": (CREDITS_PER_VERIFICATION, REP_G_AWARD_PER_VERIFICATION),
            "discovery": (CREDITS_PER_DISCOVERY, 0)
        }.get(event_type, (0, 0))
        
        credits_awarded, rep_g_earned = rewards
        
        self.compute_credits += credits_awarded
        self.rep_g += rep_g_earned
        
        logger.info(f"Consensus achieved for {cid}. Awarded +{credits_awarded} credits and +{rep_g_earned} REP-G.")
        return self.compute_credits, self.rep_g

    def can_influence_consensus(self) -> bool:
        """Sybil Resistance: Only nodes with REP-G can influence consensus."""
        return self.rep_g >= MIN_STAKE

    def spend_credit(self) -> bool:
        """Spend one compute credit for a Central Brain (LLM) query."""
        if self.compute_credits < CREDITS_PER_BRAIN_QUERY:
            return False
        self.compute_credits -= CREDITS_PER_BRAIN_QUERY
        return True

