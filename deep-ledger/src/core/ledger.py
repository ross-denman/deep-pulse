#!/usr/bin/env python3
"""
Deep Ledger — Ledger Module (JSON-LD)

Implements the Deep Ledger Intelligence Standard v1.0 for creating,
signing, and appending entries to harvest/ledger.jsonld.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.identity import NodeIdentity, load_identity

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LEDGER_FILE = PROJECT_ROOT / "harvest" / "ledger.jsonld"

# Deep Ledger Intelligence Standard v1.0
CONTEXT = "Deep Ledger Intelligence Standard v1.0"


def compute_cid(data: dict[str, Any], metadata: dict[str, Any]) -> str:
    """Compute a Content Identifier (CID) for a ledger entry.

    The CID is the SHA-256 hash of the canonical JSON representation
    of the data + metadata fields.

    Args:
        data: The intelligence payload.
        metadata: The metadata (timestamp, source, scout_id).

    Returns:
        A hex-encoded SHA-256 hash string prefixed with 'cid:'.
    """
    canonical = json.dumps({"data": data, "metadata": metadata}, sort_keys=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"cid:{digest}"


def create_entry(
    identity: NodeIdentity,
    data: dict[str, Any],
    source_url: str,
    scout_id: str = "genesis",
    status: str = "speculative",
) -> dict[str, Any]:
    """Create a new signed Ledger entry.

    The `data` parameter should be a validated Pydantic model dict
    (via model_dump()) for Scout outputs, ensuring type safety through
    the Intelligence Gate. Raw dicts are still accepted for backward
    compatibility (e.g., Genesis entries).

    Args:
        identity: The signing node's identity.
        data: The intelligence payload (ideally from model_dump()).
        source_url: The URL from which this data was sourced.
        scout_id: Identifier for the scout that discovered this data.
        status: One of 'speculative', 'pending_verification', 'verified'.

    Returns:
        A complete JSON-LD entry dict ready to be appended to the Ledger.
    """
    metadata = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_url": source_url,
        "scout_id": scout_id,
        "node_id": identity.node_id,
        "status": status,
    }

    cid = compute_cid(data, metadata)

    # Sign the CID + data canonical form
    signable = json.dumps({"id": cid, "data": data}, sort_keys=True).encode("utf-8")
    signature = identity.sign(signable)

    entry = {
        "@context": CONTEXT,
        "id": cid,
        "data": data,
        "metadata": metadata,
        "proof": {
            "type": "Ed25519Signature2020",
            "verificationMethod": identity.public_key_hex,
            "signature": signature,
        },
    }

    return entry


def append_entry(entry: dict[str, Any]) -> None:
    """Append a signed entry to the Ledger file.

    The Ledger file is a JSON array of entries.

    Args:
        entry: A complete JSON-LD entry dict.
    """
    LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)

    ledger: list[dict[str, Any]] = []
    if LEDGER_FILE.exists():
        try:
            with open(LEDGER_FILE, "r") as f:
                content = f.read().strip()
                if content:
                    ledger = json.loads(content)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("Failed to read existing ledger, starting fresh: %s", e)
            ledger = []

    ledger.append(entry)

    with open(LEDGER_FILE, "w") as f:
        json.dump(ledger, f, indent=2, ensure_ascii=False)

    logger.info("Ledger entry appended: %s", entry["id"])


def read_ledger() -> list[dict[str, Any]]:
    """Read all entries from the Ledger.

    Returns:
        A list of JSON-LD entry dicts.
    """
    if not LEDGER_FILE.exists():
        return []

    try:
        with open(LEDGER_FILE, "r") as f:
            return json.loads(f.read().strip() or "[]")
    except (json.JSONDecodeError, IOError) as e:
        logger.error("Failed to read ledger: %s", e)
        return []


def verify_entry(entry: dict[str, Any]) -> bool:
    """Verify the cryptographic integrity of a Ledger entry.

    Checks that the proof signature matches the entry's id + data.

    Args:
        entry: A Ledger entry dict.

    Returns:
        True if the signature is valid.
    """
    from src.core.identity import verify_signature_with_pubkey

    try:
        signable = json.dumps(
            {"id": entry["id"], "data": entry["data"]}, sort_keys=True
        ).encode("utf-8")

        return verify_signature_with_pubkey(
            entry["proof"]["verificationMethod"],
            signable,
            entry["proof"]["signature"],
        )
    except (KeyError, Exception) as e:
        logger.error("Entry verification failed: %s", e)
        return False


def create_genesis_entry(identity: NodeIdentity) -> dict[str, Any]:
    """Create the Genesis entry — the first entry in the Ledger.

    This entry records the birth of this node and its first Intelligence Perimeter.

    Args:
        identity: The node's sovereign identity.

    Returns:
        A signed Genesis entry.
    """
    data = {
        "type": "GenesisEntry",
        "title": "Deep Ledger Node Initialization",
        "description": (
            "This node has been initialized as a sovereign participant "
            "in the Deep Pulse Intelligence Swarm."
        ),
        "intelligence_perimeter": ["Meta Infrastructure", "LEAP District"],
        "node_alias": "Node 0x0001",
    }

    return create_entry(
        identity=identity,
        data=data,
        source_url="local://identity-bootstrap",
        scout_id="genesis",
        status="verified",
    )
