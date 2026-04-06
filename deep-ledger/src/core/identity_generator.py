#!/usr/bin/env python3
"""
Deep Ledger — Ed25519 Identity Generator

Generates a sovereign Ed25519 keypair for this node.
The public key becomes the Node ID.
The private key is stored in .env (git-ignored) and used to sign Ledger entries.

Usage:
    python src/core/identity_generator.py
"""

import hashlib
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


def generate_keypair() -> tuple[str, str]:
    """Generate an Ed25519 keypair.

    Returns:
        Tuple of (public_key_hex, private_key_hex).
    """
    private_key = Ed25519PrivateKey.generate()

    # Extract raw bytes
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    return public_bytes.hex(), private_bytes.hex()


def derive_node_id(public_key_hex: str) -> str:
    """Derive a human-readable Node ID from the public key.

    Uses the first 8 bytes of the SHA-256 hash of the public key,
    prefixed with '0x'.

    Args:
        public_key_hex: The hex-encoded Ed25519 public key.

    Returns:
        A Node ID string like '0x0001abcd...'.
    """
    digest = hashlib.sha256(bytes.fromhex(public_key_hex)).hexdigest()
    return f"0x{digest[:16]}"


def write_env(private_key_hex: str, public_key_hex: str, node_id: str) -> None:
    """Write or update the .env file with identity and default configuration.

    Args:
        private_key_hex: The hex-encoded Ed25519 private key.
        public_key_hex: The hex-encoded Ed25519 public key.
        node_id: The derived Node ID.
    """
    env_lines: dict[str, str] = {}

    # Read existing .env if present
    if ENV_FILE.exists():
        with open(ENV_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    env_lines[key.strip()] = value.strip()

    # Set identity fields
    env_lines["NODE_PRIVATE_KEY"] = private_key_hex
    env_lines["NODE_PUBLIC_KEY"] = public_key_hex
    env_lines["NODE_ID"] = node_id

    # Set defaults if not already present
    env_lines.setdefault("OPENROUTER_API_KEY", "")
    env_lines.setdefault("MODEL", "openrouter/free")
    env_lines.setdefault("NEO4J_URI", "bolt://localhost:7687")
    env_lines.setdefault("NEO4J_USER", "neo4j")
    env_lines.setdefault("NEO4J_PASSWORD", "deep-ledger-secret")

    # Write back
    with open(ENV_FILE, "w") as f:
        f.write("# ====================================\n")
        f.write("# Deep Ledger — Node Configuration\n")
        f.write("# THIS FILE IS GIT-IGNORED. DO NOT COMMIT.\n")
        f.write("# ====================================\n\n")
        f.write("# --- Sovereign Identity (Ed25519) ---\n")
        f.write(f"NODE_PRIVATE_KEY={env_lines.pop('NODE_PRIVATE_KEY')}\n")
        f.write(f"NODE_PUBLIC_KEY={env_lines.pop('NODE_PUBLIC_KEY')}\n")
        f.write(f"NODE_ID={env_lines.pop('NODE_ID')}\n\n")
        f.write("# --- LLM Provider ---\n")
        f.write(f"OPENROUTER_API_KEY={env_lines.pop('OPENROUTER_API_KEY', '')}\n")
        f.write(f"MODEL={env_lines.pop('MODEL', 'openrouter/free')}\n\n")
        f.write("# --- Neo4j ---\n")
        f.write(f"NEO4J_URI={env_lines.pop('NEO4J_URI', 'bolt://localhost:7687')}\n")
        f.write(f"NEO4J_USER={env_lines.pop('NEO4J_USER', 'neo4j')}\n")
        f.write(f"NEO4J_PASSWORD={env_lines.pop('NEO4J_PASSWORD', 'deep-ledger-secret')}\n\n")

        # Write any remaining keys
        if env_lines:
            f.write("# --- Additional ---\n")
            for key, value in env_lines.items():
                f.write(f"{key}={value}\n")

    print(f"  ✅ .env written to {ENV_FILE}")


def main() -> None:
    """Bootstrap the node identity."""
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║   DEEP LEDGER — Identity Bootstrap       ║")
    print("  ║   Generating Ed25519 Sovereign Identity   ║")
    print("  ╚══════════════════════════════════════════╝")
    print()

    # Check if identity already exists
    if ENV_FILE.exists():
        with open(ENV_FILE, "r") as f:
            content = f.read()
        if "NODE_PRIVATE_KEY=" in content:
            # Extract existing key to check if it's populated
            for line in content.splitlines():
                if line.startswith("NODE_PRIVATE_KEY=") and len(line.split("=", 1)[1].strip()) > 0:
                    print("  ⚠️  Identity already exists in .env.")
                    print("  To regenerate, delete the NODE_PRIVATE_KEY line from .env first.")
                    # Still print the existing identity
                    for line2 in content.splitlines():
                        if line2.startswith("NODE_ID="):
                            print(f"  🔑 Existing Node ID: {line2.split('=', 1)[1]}")
                        if line2.startswith("NODE_PUBLIC_KEY="):
                            print(f"  🌐 Public Key: {line2.split('=', 1)[1][:32]}...")
                    return

    public_key_hex, private_key_hex = generate_keypair()
    node_id = derive_node_id(public_key_hex)

    write_env(private_key_hex, public_key_hex, node_id)

    print(f"  🔑 Node ID:     {node_id}")
    print(f"  🌐 Public Key:  {public_key_hex[:32]}...")
    print(f"  🔒 Private Key: [REDACTED — stored in .env]")
    print()
    print("  ✅ Genesis identity created. You are Node 0x0001.")
    print("  📜 This key will sign your first Ledger entries.")
    print()


if __name__ == "__main__":
    main()
