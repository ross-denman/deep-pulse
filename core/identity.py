#!/usr/bin/env python3
"""
The Chronicle - Identity Module

Loads the Ed25519 identity from .env and provides signing/verification helpers.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from dotenv import load_dotenv

from src.public.core.crypto import sign_data, verify_signature


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class OutpostIdentity:
    """Represents the sovereign identity of a The Chronicle outpost."""

    outpost_id: str
    public_key_hex: str
    private_key: Ed25519PrivateKey
    public_key: Ed25519PublicKey

    def sign(self, data: bytes) -> str:
        """Sign arbitrary data with this outpost's private key."""
        # Convert private key back to bytes to use the crypto mechanism
        # This ensures parity between the object-based sign and hex-based sign
        priv_bytes = self.private_key.private_bytes_raw()
        return sign_data(priv_bytes.hex(), data)

    def verify(self, data: bytes, signature_hex: str) -> bool:
        """Verify a seal against this outpost's public key."""
        return verify_signature(self.public_key_hex, data, signature_hex)


def load_identity() -> OutpostIdentity:
    """Load the outpost identity from environment variables.

    Returns:
        An OutpostIdentity instance.

    Raises:
        ValueError: If identity keys are missing from .env.
    """
    private_key_hex = os.getenv("OUTPOST_KEY")
    public_key_hex = os.getenv("OUTPOST_PUBLIC_KEY")
    outpost_id = os.getenv("OUTPOST_ID")

    if not private_key_hex or not public_key_hex or not outpost_id:
        raise ValueError(
            "Outpost identity not found. Run 'python src/core/identity_generator.py' first."
        )

    private_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_key_hex))
    public_key = private_key.public_key()

    return OutpostIdentity(
        outpost_id=outpost_id,
        public_key_hex=public_key_hex,
        private_key=private_key,
        public_key=public_key,
    )


def verify_signature_with_pubkey(
    public_key_hex: str, data: bytes, signature_hex: str
) -> bool:
    """Verify a seal using a raw public key (for verifying other outposts)."""
    return verify_signature(public_key_hex, data, signature_hex)
