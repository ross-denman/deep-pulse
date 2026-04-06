#!/usr/bin/env python3
"""
Deep Ledger — Identity Module

Loads the Ed25519 identity from .env and provides signing/verification helpers.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
)
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class NodeIdentity:
    """Represents the sovereign identity of a Deep Ledger node."""

    node_id: str
    public_key_hex: str
    private_key: Ed25519PrivateKey
    public_key: Ed25519PublicKey

    def sign(self, data: bytes) -> str:
        """Sign arbitrary data with this node's private key.

        Args:
            data: The raw bytes to sign.

        Returns:
            Hex-encoded Ed25519 signature.
        """
        signature = self.private_key.sign(data)
        return signature.hex()

    def verify(self, data: bytes, signature_hex: str) -> bool:
        """Verify a signature against this node's public key.

        Args:
            data: The original data bytes.
            signature_hex: The hex-encoded signature to verify.

        Returns:
            True if the signature is valid.

        Raises:
            cryptography.exceptions.InvalidSignature: If the signature is invalid.
        """
        try:
            self.public_key.verify(bytes.fromhex(signature_hex), data)
            return True
        except Exception:
            return False


def load_identity() -> NodeIdentity:
    """Load the node identity from environment variables.

    Returns:
        A NodeIdentity instance.

    Raises:
        ValueError: If identity keys are missing from .env.
    """
    private_key_hex = os.getenv("NODE_PRIVATE_KEY")
    public_key_hex = os.getenv("NODE_PUBLIC_KEY")
    node_id = os.getenv("NODE_ID")

    if not private_key_hex or not public_key_hex or not node_id:
        raise ValueError(
            "Node identity not found. Run 'python src/core/identity_generator.py' first."
        )

    private_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_key_hex))
    public_key = private_key.public_key()

    return NodeIdentity(
        node_id=node_id,
        public_key_hex=public_key_hex,
        private_key=private_key,
        public_key=public_key,
    )


def verify_signature_with_pubkey(
    public_key_hex: str, data: bytes, signature_hex: str
) -> bool:
    """Verify a signature using a raw public key (for verifying other nodes).

    Args:
        public_key_hex: Hex-encoded Ed25519 public key.
        data: The original data bytes.
        signature_hex: The hex-encoded signature.

    Returns:
        True if valid, False otherwise.
    """
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey as PubKey,
        )

        pub = PubKey.from_public_bytes(bytes.fromhex(public_key_hex))
        pub.verify(bytes.fromhex(signature_hex), data)
        return True
    except Exception:
        return False
