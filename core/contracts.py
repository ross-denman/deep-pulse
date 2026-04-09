#!/usr/bin/env python3
"""
The Chronicle - Shared Bridge Contracts
Phase 5: The Incentive Handshake

Defines the cryptographic and state-based contracts for the mesh.
Both Auditors and the Notary use these models to communicate state changes.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Handshake Models Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

class ClaimHandshake(BaseModel):
    """A signed intent-to-hunt from an Auditor."""
    inquiry_id: str
    outpost_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    lease_hours: int = 24
    signature: str # Signature of (inquiry_id + outpost_id + timestamp)

class VerificationRequest(BaseModel):
    """Publicly gossiped signal that a Grain is ready for verification."""
    grain_id: str # The CID of the discovery
    title: str
    gravity: float = 5.0
    grain_bounty: int = 25
    finder_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    claim_handshake: ClaimHandshake # The original Handshake that started the hunt
    status: Literal["OPEN", "PENDING_VERIFICATION", "SETTLED"] = "OPEN"

class ValidationAttestation(BaseModel):
    """A signed proof of verification from a peer Auditor."""
    grain_id: str
    verifier_id: str
    atttestation_type: Literal["CONFIRM", "CONFLICT"] = "CONFIRM"
    finding_summary: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    signature: str # Signature of (grain_id + verifier_id + attestation_type)

class ProofOfDiscovery(BaseModel):
    """The final submission package for settlement."""
    grain_id: str
    payload: Dict[str, Any]
    attestations: List[ValidationAttestation] = Field(default_factory=list)
    handshake: ClaimHandshake
    notary_audit_score: Optional[float] = None
