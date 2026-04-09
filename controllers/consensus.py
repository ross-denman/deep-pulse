#!/usr/bin/env python3
"""
Deep Ledger - Consensus Controller (Policy Layer)

Orchestrates the validation of Ledger entries and the 2+1 Quorum voting logic.
Decouples consensus policy from mechanical signature verification.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from core.crypto import verify_signature
from core.identity import OutpostIdentity
from core.network import MeshClient
from core.chronicle import verify_entry, read_ledger, CHRONICLE_FILE as LEDGER_FILE, calculate_consensus_weight, create_entry
from core.reputation import ReputationService
from core.sources import source_validator
import json
import os

logger = logging.getLogger(__name__)

class ConsensusController:
    """Orchestrates validation and quorum consensus for ledger entries."""

    def __init__(
        self, 
        client: MeshClient, 
        identity: OutpostIdentity, 
        rep_service: ReputationService,
        threshold: float = 1.0
    ):
        """Initialize the Consensus Controller.

        Args:
            client: The MeshClient for network communication.
            identity: The OutpostIdentity for signing votes.
            rep_service: The ReputationService for weighted voting.
            threshold: Cumulative weight required for consensus (e.g. 1.0).
        """
        self.client = client
        self.identity = identity
        self.rep_service = rep_service
        self.threshold = threshold

    def validate_entry(self, entry: Dict[str, Any]) -> bool:
        """High-level validation of a Ledger entry.

        Args:
            entry: The entry dict to validate.

        Returns:
            True if entries are cryptographically valid and meet baseline criteria.
        """
        # 1. Genesis Safeguard
        if entry.get("id") == "chronicle:genesis":
            logger.info("Genesis entry detected. Baseline trust established.")
            return True

        # 2. Cryptographic Integrity Check
        # Utilizes the core/chronicle verify_entry which uses crypto/verify_signature
        if not verify_entry(entry):
            logger.error(f"Integrity check failed for entry {entry.get('id', 'unknown')}")
            return False

        logger.info(f"Entry {entry['id']} passed high-level validation.")
        return True

    def cast_vote(self, cid: str) -> Optional[Dict[str, Any]]:
        """Orchestrate a sovereign vote/attestation for a specific CID.

        Args:
            cid: The Content Identifier to attest to.

        Returns:
            The API response from the Bridge sign endpoint.
        """
        logger.info(f"Preparing attestation for CID: {cid}")
        
        try:
            # Cast the vote via the Mesh Client
            res = self.client.sign_entry(cid, self.identity.outpost_id)
            
            weight = res.get("weight", 0.0)
            status = res.get("status", "unknown")
            
            logger.info(f"Vote cast. Current weight: {weight}/{self.threshold}. Status: {status}")
            
            if status == "verified" or weight >= self.threshold:
                logger.info(f"[*] CONSENSUS REACHED for {cid}.")
                
            return res
        except Exception as e:
            logger.error(f"Failed to cast vote for {cid}: {e}")
            return None

    def audit_quorum(self, entry: Dict[str, Any]) -> float:
        """Analyze the current quorum weight based on dynamic reputation tiers and source weighting."""
        return calculate_consensus_weight(entry, self.rep_service)

    def check_conflicts(self, new_entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check for Epistemic Conflicts between the new entry and established Institutional Anchors."""
        ledger = read_ledger()
        source_url = new_entry.get("metadata", {}).get("source_url", "")
        source_meta = source_validator.get_source_metadata(source_url)
        
        # If the new source is ephemeral/volatile, check if it contradicts verified institutional anchors
        if source_meta.get("is_volatile"):
            for entry in ledger:
                if entry.get("metadata", {}).get("status") == "verified":
                    anchor_url = entry.get("metadata", {}).get("source_url", "")
                    anchor_meta = source_validator.get_source_metadata(anchor_url)
                    
                    if anchor_meta.get("is_institutional"):
                        # Simplified contradiction check for MVP: same subject, different data
                        if entry.get("data", {}).get("title") == new_entry.get("data", {}).get("title"):
                            if entry.get("data", {}).get("payload") != new_entry.get("data", {}).get("payload"):
                                logger.warning(f"[WAR] EPISTEMIC CONFLICT: Social source contradiction against Institutional Anchor for {entry['id']}")
                                return self.generate_conflict_event(entry, new_entry)
        return None

    def generate_conflict_event(self, anchor: Dict[str, Any], contradiction: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a ConflictEvent to be pushed to the Chronicle."""
        event_data = {
            "type": "ConflictEvent",
            "anchor_cid": anchor["id"],
            "contradiction_cid": contradiction["id"],
            "description": f"Social contradiction detected against Institutional Anchor ({anchor['metadata']['source_url']})",
            "status": "ST_VOLATILE"
        }
        
        event_entry = create_entry(
            identity=self.identity,
            data=event_data,
            source_url="system://consensus/conflict-handler",
            probe_id="SovereignNotary",
            status="verified" # ConflictEvents are authoritative facts of discrepancy
        )
        return event_entry

    def settle_speculative(self, all_missions: bool = False) -> Tuple[int, int]:
        """Promote speculative entries to verified status (Batch Settlement)."""
        ledger = read_ledger()
        if not ledger:
            return 0, 0

        to_settle = [e for e in ledger if e.get("metadata", {}).get("status") == "speculative"]
        if not to_settle:
            return 0, len(ledger)

        count = 0
        for entry in to_settle:
            # In a real mesh, we'd check if weight >= threshold here
            # For this dispatcher refactor, we maintain the "Genesis Settlement" behavior
            entry["metadata"]["status"] = "verified"
            count += 1
        
        try:
            with open(LEDGER_FILE, "w") as f:
                json.dump(ledger, f, indent=2)
            return count, len(ledger)
        except Exception as e:
            logger.error(f"Failed to save settled ledger: {e}")
            return 0, len(ledger)

    def run_metabolic_audit(self) -> Dict[str, Any]:
        """Aggregate resource grid states from the metabolism engine."""
        try:
            from core.metabolism import metabolism
            return {
                "power": metabolism.get_grid_state("power") or metabolism._grid_caps.get("power", 0),
                "water": metabolism.get_grid_state("water") or metabolism._grid_caps.get("water", 0),
                "wastewater": metabolism.get_grid_state("wastewater") or metabolism._grid_caps.get("wastewater", 0)
            }
        except ImportError:
            return {}

    def audit_system_integrity(self) -> Tuple[bool, int, int]:
        """Check the consistency of all signatures in the local chronicle."""
        ledger = read_ledger()
        if not ledger:
            return True, 0, 0
            
        invalid = 0
        for entry in ledger:
            if not self.validate_entry(entry):
                invalid += 1
        
        return invalid == 0, len(ledger) - invalid, len(ledger)
