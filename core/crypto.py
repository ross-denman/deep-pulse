#!/usr/bin/env python3
"""
Deep Ledger - Cryptographic Mechanism Module

Low-level utilities for SHA-256 hashing and Ed25519 signing.
Decoupled from high-level Identity models to allow lightweight use.
"""

import hashlib
import json
import logging
from typing import Any
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

logger = logging.getLogger(__name__)

def canonical_json(data: Any) -> bytes:
    """Return a stable, canonical JSON representation of data."""
    return json.dumps(
        data, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")

def sha256_hash(data: bytes) -> str:
    """Compute a hex-encoded SHA-256 hash of provided bytes."""
    return hashlib.sha256(data).hexdigest()

def sign_data(private_key_hex: str, data: bytes) -> str:
    """Sign data with an Ed25519 private key.

    Args:
        private_key_hex: Hex-encoded Ed25519 private key.
        data: Raw bytes to sign.

    Returns:
        Hex-encoded signature string.
    """
    private_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_key_hex))
    signature = private_key.sign(data)
    return signature.hex()

def verify_signature(public_key_hex: str, data: bytes, signature_hex: str) -> bool:
    """Verify an Ed25519 signature against a public key.

    Args:
        public_key_hex: Hex-encoded Ed25519 public key.
        data: Original data bytes.
        signature_hex: Hex-encoded signature seal.

    Returns:
        True if valid, False otherwise.
    """
    try:
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        public_key.verify(bytes.fromhex(signature_hex), data)
        return True
    except Exception:
        return False

# Content Identifiers (CIDs) from original chronicle.py

def compute_cid(data: dict[str, Any], metadata: dict[str, Any]) -> str:
    """Compute a Content Identifier (CID) for a ledger entry."""
    canonical = canonical_json({"data": data, "metadata": metadata})
    digest = sha256_hash(canonical)
    return f"cid:{digest}"

def compute_evidence_cid(raw_data: bytes) -> str:
    """Compute a Content Identifier (CID) for raw discovery evidence."""
    digest = sha256_hash(raw_data)
    return f"cid:evidence:{digest}"

def compute_entity_id(name: str, category: str) -> str:
    """Compute a deterministic CID for an entity."""
    normalized_name = name.strip().lower()
    normalized_category = category.strip().lower()
    combined = f"{normalized_name}:{normalized_category}".encode("utf-8")
    digest = sha256_hash(combined)
    return f"cid:entity:{digest}"
