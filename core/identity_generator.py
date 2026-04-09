#!/usr/bin/env python3
"""
The Chronicle - Probe Seal Generator

Generates a sovereign Ed25519 "Seal" (keypair) for this Probe.
The public key derivation becomes the Probe ID.
The private seal is stored in .env (git-ignored) and used to sign **The Chronicle** entries.

Usage:
    python src/core/identity_generator.py
"""

import hashlib
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization


# Robust PROJECT_ROOT calculation
_current_file = Path(__file__).resolve()
# If this file is in 'core/', parent is 'core/', parent.parent is root.
# If this file is in 'src/public/core/', we need more parents.
if "src" in _current_file.parts:
    PROJECT_ROOT = _current_file.parent.parent.parent.parent
else:
    PROJECT_ROOT = _current_file.parent.parent

ENV_FILE = PROJECT_ROOT / ".env"


def generate_keypair() -> tuple[str, str]:
    """Generate an Ed25519 keypair."""
    private_key = Ed25519PrivateKey.generate()
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


def derive_probe_id(public_key_hex: str) -> str:
    """Derive a human-readable Probe ID from the public key."""
    digest = hashlib.sha256(bytes.fromhex(public_key_hex)).hexdigest()
    return f"0x{digest[:16]}"


def write_env(private_key_hex: str, public_key_hex: str, probe_id: str) -> None:
    """Write or update the .env file with identity and default configuration."""
    env_lines: dict[str, str] = {}
    if ENV_FILE.exists():
        with open(ENV_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    env_lines[key.strip()] = value.strip()

    env_lines["OUTPOST_KEY"] = private_key_hex
    env_lines["OUTPOST_PUBLIC_KEY"] = public_key_hex
    env_lines["OUTPOST_ID"] = probe_id

    env_lines.setdefault("LLM_API_KEY", "")
    env_lines.setdefault("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    env_lines.setdefault("LLM_MODEL", "openrouter/free")
    env_lines.setdefault("BRAVE_API_KEY", "")
    env_lines.setdefault("NEO4J_URI", "bolt://localhost:7687")
    env_lines.setdefault("NEO4J_USER", "nexus_operator")
    env_lines.setdefault("NEO4J_PASSWORD", "deep-ledger-secret")
    env_lines.setdefault("NEO4J_DATABASE", "neo4j")

    with open(ENV_FILE, "w") as f:
        f.write("# ====================================\n")
        f.write("# The Chronicle - Probe Configuration\n")
        f.write("# THIS FILE IS GIT-IGNORED. DO NOT COMMIT.\n")
        f.write("# ====================================\n\n")
        f.write("# --- Sovereign Seal (Ed25519) ---\n")
        f.write(f"OUTPOST_KEY={env_lines.pop('OUTPOST_KEY')}\n")
        f.write(f"OUTPOST_PUBLIC_KEY={env_lines.pop('OUTPOST_PUBLIC_KEY')}\n")
        f.write(f"OUTPOST_ID={env_lines.pop('OUTPOST_ID')}\n\n")
        f.write("# --- Core Intelligence --- \n")
        f.write(f"LLM_API_KEY={env_lines.pop('LLM_API_KEY', '')}\n")
        f.write(f"LLM_BASE_URL={env_lines.pop('LLM_BASE_URL', 'https://openrouter.ai/api/v1')}\n")
        f.write(f"LLM_MODEL={env_lines.pop('LLM_MODEL', 'openrouter/free')}\n\n")
        f.write("# --- Search Engine (Brave) ---\n")
        f.write(f"BRAVE_API_KEY={env_lines.pop('BRAVE_API_KEY', '')}\n\n")
        f.write("# --- Neo4j (Notary Only) ---\n")
        f.write(f"NEO4J_URI={env_lines.pop('NEO4J_URI', 'bolt://localhost:7687')}\n")
        f.write(f"NEO4J_USER={env_lines.pop('NEO4J_USER', 'nexus_operator')}\n")
        f.write(f"NEO4J_PASSWORD={env_lines.pop('NEO4J_PASSWORD', 'deep-ledger-secret')}\n")
        f.write(f"NEO4J_DATABASE={env_lines.pop('NEO4J_DATABASE', 'neo4j')}\n\n")
        f.write("# --- KuzuDB (Outpost Default) ---\n")
        f.write(f"KUZU_DB_PATH={env_lines.pop('KUZU_DB_PATH', 'harvest/kuzu_db')}\n\n")
        if env_lines:
            f.write("# --- Additional ---\n")
            for key, value in env_lines.items():
                f.write(f"{key}={value}\n")

    print(f"  [OK] .env written to {ENV_FILE}")


def main() -> None:
    """Bootstrap the node identity."""
    # Fix for Windows encoding issues
    if sys.platform == "win32":
        try:
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        except Exception:
            pass

    print()
    print("  +------------------------------------------+")
    print("  |   THE CHRONICLE - Identity Bootstrap     |")
    print("  |   Generating Ed25519 Sovereign Identity   |")
    print("  +------------------------------------------+")
    print()

    if ENV_FILE.exists():
        with open(ENV_FILE, "r") as f:
            content = f.read()
        if "OUTPOST_KEY=" in content:
            for line in content.splitlines():
                if line.startswith("OUTPOST_KEY=") and len(line.split("=", 1)[1].strip()) > 0:
                    print("  [WARNING] Sovereign Seal already exists in .env.")
                    print("  To regenerate, delete the OUTPOST_KEY line from .env first.")
                    for line2 in content.splitlines():
                        if line2.startswith("OUTPOST_ID="):
                            print(f"  [ID] Existing Outpost ID: {line2.split('=', 1)[1]}")
                        if line2.startswith("OUTPOST_PUBLIC_KEY="):
                            print(f"  [PUB] Public Key: {line2.split('=', 1)[1][:32]}...")
                    return

    public_key_hex, private_key_hex = generate_keypair()
    probe_id = derive_probe_id(public_key_hex)
    write_env(private_key_hex, public_key_hex, probe_id)

    print(f"  [ID] Probe ID:    {probe_id}")
    print(f"  [PUB] Public Key:  {public_key_hex[:32]}...")
    print(f"  [SEC] Private Seal:[REDACTED - stored in .env]")
    print()
    print("  [OK] Genesis seal created. You are now a Mesh Probe.")
    print("  [DOC] This seal will sign your entries in **The Chronicle**.")
    print()


if __name__ == "__main__":
    main()

