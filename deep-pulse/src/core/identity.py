#!/usr/bin/env python3
"""
Deep Pulse — Identity Service

Manages Ed25519 identities for swarm nodes.
Includes a Key Rotation Policy to allow secure identity transitions.
"""

import os
import logging
from datetime import datetime, timezone
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from dotenv import load_dotenv, set_key

logger = logging.getLogger(__name__)

class IdentityManager:
    """Manages the node's Ed25519 identity and rotation."""

    def __init__(self, env_path: str = ".env"):
        self.env_path = env_path
        load_dotenv(self.env_path)
        self._private_key = None
        self._public_key = None

    def generate_identity(self):
        """Generates a new Ed25519 keypair and saves to .env."""
        logger.info("Generating new Ed25519 identity...")
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

        private_hex = private_bytes.hex()
        public_hex = public_bytes.hex()
        node_id = f"0x{public_hex[:16]}" # Node ID is first 16 chars of pubkey

        if not os.path.exists(self.env_path):
            with open(self.env_path, "w") as f:
                f.write("")

        set_key(self.env_path, "NODE_PRIVATE_KEY", private_hex)
        set_key(self.env_path, "NODE_PUBLIC_KEY", public_hex)
        set_key(self.env_path, "NODE_ID", node_id)
        
        logger.info(f"Identity generated. Node ID: {node_id}")
        self._private_key = private_key
        self._public_key = public_key
        return node_id

    def load_identity(self):
        """Loads identity from .env."""
        private_hex = os.getenv("NODE_PRIVATE_KEY")
        if not private_hex:
            return None

        private_bytes = bytes.fromhex(private_hex)
        self._private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
        self._public_key = self._private_key.public_key()
        return os.getenv("NODE_ID")

    def rotate_identity(self):
        """
        Rotates the node's identity.
        1. Archives the old key in keys/retired/
        2. Generates a new identity
        3. Signs the new public key with the old private key (Transition Proof)
        """
        old_node_id = os.getenv("NODE_ID")
        old_pub_hex = os.getenv("NODE_PUBLIC_KEY")
        
        if not self._private_key:
            self.load_identity()
            
        if not self._private_key:
            raise ValueError("No identity to rotate.")

        # Archive old
        retired_dir = "keys/retired"
        os.makedirs(retired_dir, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        with open(f"{retired_dir}/key_{old_node_id}_{timestamp}.hex", "w") as f:
            f.write(os.getenv("NODE_PRIVATE_KEY"))

        # Generate new
        new_node_id = self.generate_identity()
        new_pub_hex = os.getenv("NODE_PUBLIC_KEY")
        
        # Sign transition
        transition_msg = f"TRANSITION:{old_pub_hex}->{new_pub_hex}".encode()
        signature = self._private_key.sign(transition_msg)
        
        set_key(self.env_path, "LAST_ROTATION_PROOF", signature.hex())
        set_key(self.env_path, "LAST_ROTATION_DATE", datetime.now(timezone.utc).isoformat())
        
        logger.info(f"Identity rotated: {old_node_id} -> {new_node_id}")
        return new_node_id

    def sign(self, data: bytes) -> bytes:
        """Signs data with the private key."""
        if not self._private_key:
            self.load_identity()
        return self._private_key.sign(data)

    def verify(self, data: bytes, signature: bytes, public_key_hex: str) -> bool:
        """Verifies a signature against a public key."""
        pub_bytes = bytes.fromhex(public_key_hex)
        pub_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
        try:
            pub_key.verify(signature, data)
            return True
        except Exception:
            return False
