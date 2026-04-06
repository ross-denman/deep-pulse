#!/usr/bin/env python3
"""
Deep Pulse — Protocol Service (Deep Ledger Intelligence Standard v1.0)

Canonical implementation of CID computation, entry schema validation,
and signature verification for the Deep Ledger ecosystem.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ConventionProtocol:
    """Canonical Protocol for Deep Ledger Intelligence Standard v1.0."""

    @staticmethod
    def compute_cid(data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """
        Computes the Unique Content Identifier (CID).
        CID = hash(data_json + metadata_json).
        """
        payload = {
            "data": data,
            "metadata": metadata
        }
        # Standardize JSON serialization for deterministic hashing
        payload_json = json.dumps(payload, sort_keys=True)
        cid_hash = hashlib.sha256(payload_json.encode()).hexdigest()
        return f"0x{cid_hash}"

    @staticmethod
    def validate_entry(entry: Dict[str, Any]) -> bool:
        """Validates that a Ledger entry matches the v1.0 standard."""
        required_fields = ["@context", "id", "data", "metadata", "proof"]
        for field in required_fields:
            if field not in entry:
                logger.warning(f"Entry missing required field: {field}")
                return False
        
        if entry.get("@context") != "Deep Ledger Intelligence Standard v1.0":
            logger.warning("Incorrect entry context.")
            return False
            
        return True

    @staticmethod
    def create_pulse_entry(
        data: Dict[str, Any], 
        metadata: Dict[str, Any], 
        identity_manager
    ) -> Dict[str, Any]:
        """Creates a signed Ledger entry."""
        cid = ConventionProtocol.compute_cid(data, metadata)
        
        # Sign the CID
        signature = identity_manager.sign(cid.encode())
        public_key = os.getenv("NODE_PUBLIC_KEY")
        
        entry = {
            "@context": "Deep Ledger Intelligence Standard v1.0",
            "id": cid,
            "data": data,
            "metadata": metadata,
            "proof": {
                "type": "Ed25519Signature2020",
                "verificationMethod": public_key,
                "signature": signature.hex()
            }
        }
        
        return entry

    @staticmethod
    def verify_entry_proof(entry: Dict[str, Any], identity_manager) -> bool:
        """Verifies the signature of an entry."""
        if not ConventionProtocol.validate_entry(entry):
            return False
            
        cid = entry.get("id")
        proof = entry.get("proof", {})
        signature_hex = proof.get("signature")
        public_key_hex = proof.get("verificationMethod")
        
        if not signature_hex or not public_key_hex:
            return False
            
        signature = bytes.fromhex(signature_hex)
        return identity_manager.verify(cid.encode(), signature, public_key_hex)
