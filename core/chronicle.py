"""
The Chronicle Module (JSON-LD)

Implements **The Chronicle** Intelligence Standard v1.2 for creating,
signing, and appending entries to harvest/chronicle.jsonld.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json

from src.public.core.identity import OutpostIdentity, load_identity
from src.public.core.crypto import (
    compute_cid,
    compute_evidence_cid,
    compute_entity_id,
    canonical_json,
    verify_signature,
)
from src.public.core.sources import source_validator

logger = logging.getLogger(__name__)

# Resolve to sovereign-notary root (soul-ledger)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
CHRONICLE_FILE = PROJECT_ROOT / "the-chronicle" / "harvest" / "chronicle.jsonld"

# Sovereign Notary — Genesis Key v1.2
CHRONICLE_HEADER = {
    "@context": "https://schema.org",
    "type": "ChronicleAnchor",
    "id": "chronicle:genesis",
    "metadata": {
        "version": "v1.2",
        "description": "The Immutable Physical Anchor of the Soul-Ledger.",
        "timestamp": "2026-04-07T12:00:00Z" # Standardized anchor point
    }
}

# The Chronicle Intelligence Standard v1.2
CONTEXT = [
    "https://schema.org",
    {
        "deep": "https://deep-ledger.io/ns#",
        "rep_g": "deep:reputationGravity",
        "gravity": "deep:grainGravity",
        "evidence_cid": "deep:evidenceCid",
        "previous_cid": "deep:previousCid",
        "outpost_id": "deep:outpostId",
        "probe_id": "deep:probeId",
        "status": "deep:status",
        "timestamp": "schema:datePublished"
    }
]


# CID functions moved to core.crypto.py


def ensure_chronicle_header() -> list[dict[str, Any]]:
    """Ensure The Chronicle file starts with the Genesis Header."""
    CHRONICLE_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    chronicle: list[dict[str, Any]] = []
    if CHRONICLE_FILE.exists():
        try:
            with open(CHRONICLE_FILE, "r") as f:
                content = f.read().strip()
                if content:
                    chronicle = json.loads(content)
        except (json.JSONDecodeError, IOError):
            chronicle = []

    if not chronicle or chronicle[0].get("id") != "chronicle:genesis":
        logger.info("🛡️  ANCHORING: Inserting Genesis Header into Public Chronicle.")
        chronicle.insert(0, CHRONICLE_HEADER)
        with open(CHRONICLE_FILE, "w") as f:
            json.dump(chronicle, f, indent=2, ensure_ascii=False)
            
    return chronicle


# CID functions moved to core.crypto.py


def create_entry(
    identity: OutpostIdentity,
    data: dict[str, Any],
    source_url: str,
    probe_id: str = "genesis",
    status: str = "speculative",
    rep_g: int = 0,
    gravity: int = 0,
    evidence_cid: str = "",
    previous_cid: str = ""
) -> dict[str, Any]:
    """Create a new sealed Chronicle entry.

    The `data` parameter should be a validated Pydantic model dict
    (via model_dump()) for Probe outputs, ensuring type safety through
    the Curiosity Gate. Raw dicts are still accepted for backward
    compatibility (e.g., Genesis entries).

    Args:
        identity: The signing Probe's identity.
        data: The intelligence payload (ideally from model_dump()).
        source_url: The URL from which this data was sourced.
        probe_id: Identifier for the probe that discovered this data.
        status: One of 'speculative', 'pending_verification', 'verified'.

    Returns:
        A complete JSON-LD entry dict ready to be appended to The Chronicle.
    """
    metadata = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_url": source_url,
        "probe_id": probe_id,
        "outpost_id": identity.outpost_id,
        "status": status,
        "rep_g": rep_g,
        "gravity": gravity,
        "evidence_cid": evidence_cid,
        "previous_cid": previous_cid
    }

    cid = compute_cid(data, metadata)

    # Sign the CID + data canonical form (The Seal)
    signable = canonical_json({"id": cid, "data": data})
    signature = identity.sign(signable)

    entry = {
        "@context": CONTEXT,
        "id": cid,
        "data": data,
        "metadata": metadata,
        "proof": {
            "type": "MultiSignature2026",
            "signatures": [
                {
                    "verificationMethod": identity.public_key_hex,
                    "seal": signature,
                    "outpost_id": identity.outpost_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ],
        },
    }

    return entry


def add_signature(entry: dict[str, Any], identity: OutpostIdentity) -> bool:
    """Add a new sovereign seal to an existing entry.
    
    Args:
        entry: The chronicle entry to sign.
        identity: The identity adding the seal.
        
    Returns:
        True if the seal was added successfully (and was unique).
    """
    # 1. Check for duplicate seal from this outpost
    existing_outposts = [sig.get("outpost_id") for sig in entry.get("proof", {}).get("signatures", [])]
    if identity.outpost_id in existing_outposts:
        logger.warning(f"Outpost {identity.outpost_id} already signed entry {entry['id']}")
        return False
        
    # 2. Sign the CID + data canonical form (must match compute_cid logic)
    signable = canonical_json({"id": entry["id"], "data": entry["data"]})
    signature = identity.sign(signable)
    
    # 3. Append seal to Multi-Sig proofs list
    new_sig = {
        "verificationMethod": identity.public_key_hex,
        "seal": signature,
        "outpost_id": identity.outpost_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    if "signatures" not in entry["proof"]:
        # Migration path for old v1.0 entries
        old_v1 = {
            "verificationMethod": entry["proof"].get("verificationMethod"),
            "signature": entry["proof"].get("signature"),
            "outpost_id": entry.get("metadata", {}).get("outpost_id", "legacy-outpost"),
            "timestamp": entry.get("metadata", {}).get("timestamp")
        }
        entry["proof"]["signatures"] = [old_v1]
        entry["proof"]["type"] = "MultiSignature2026"
        del entry["proof"]["verificationMethod"]
        del entry["proof"]["signature"]
        
    entry["proof"]["signatures"].append(new_sig)
    logger.info(f"Added seal from {identity.outpost_id} to {entry['id']}")
    return True


def append_entry(entry: dict[str, Any]) -> None:
    """Append a sealed entry to The Chronicle file."""
    chronicle = ensure_chronicle_header()
    chronicle.append(entry)

    with open(CHRONICLE_FILE, "w") as f:
        json.dump(chronicle, f, indent=2, ensure_ascii=False)

    logger.info("Chronicle entry appended: %s", entry["id"])


def read_ledger() -> list[dict[str, Any]]:
    """Read all entries from the Chronicle.

    Returns:
        A list of JSON-LD entry dicts.
    """
    if not CHRONICLE_FILE.exists():
        return [CHRONICLE_HEADER]

    try:
        with open(CHRONICLE_FILE, "r") as f:
            return json.loads(f.read().strip() or "[]")
    except (json.JSONDecodeError, IOError) as e:
        logger.error("Failed to read chronicle: %s", e)
        return [CHRONICLE_HEADER]


def get_latest_cid() -> str:
    """Read the latest entry's CID from the Ledger.

    Returns:
        The CID of the last entry, or empty string if ledger is empty.
    """
    ledger = read_ledger()
    if not ledger:
        return ""
    return ledger[-1].get("id", "")


def verify_entry(entry: dict[str, Any]) -> bool:
    """Verify the cryptographic integrity of all signatures in a Ledger entry.

    Checks that every signature in the Multi-Sig list matches the entry's id + data.

    Args:
        entry: A Ledger entry dict.

    Returns:
        True if ALL signatures are valid or if it is the Genesis header.
    """
    if entry.get("id") == "chronicle:genesis":
        return True

    try:
        signable = canonical_json({"id": entry["id"], "data": entry["data"]})

        # Multi-Sig check
        proof = entry.get("proof", {})
        signatures = proof.get("signatures", [])
        
        if not signatures:
            # Fallback for old v1.0 structure if not migrated
            return verify_signature_with_pubkey(
                proof.get("verificationMethod"),
                signable,
                proof.get("signature"),
            )

        for sig in signatures:
            valid = verify_signature(
                sig["verificationMethod"],
                signable,
                sig["seal" if "seal" in sig else "signature"],
            )
            if not valid:
                logger.error(f"Invalid seal from {sig.get('outpost_id')} in {entry['id']}")
                return False
                
        return True
    except (KeyError, Exception) as e:
        logger.error("Entry verification failed: %s", e)
        return False


def calculate_consensus_weight(entry: dict[str, Any], rep_service) -> float:
    """Calculate the cumulative reputation weight for this entry.
    
    ANTI-SELF-VERIFICATION: Weight of the originating outpost is EXCLUDED
    from verification quorum weight.
    
    Args:
        entry: The ledger entry to weight.
        rep_service: The ReputationService instance.
        
    Returns:
        Total external weight as a float.
    """
    originator_id = entry.get("metadata", {}).get("outpost_id")
    signatures = entry.get("proof", {}).get("signatures", [])
    total_weight = 0.0
    external_sigs = 0
    
    for sig in signatures:
        outpost_id = sig.get("outpost_id")
        
        # Anti-Self-Verification: Skip weight calculation if it's the originator
        if outpost_id == originator_id:
            logger.debug(f"Consensus: Skipping originator weight for {outpost_id} on {entry['id']}")
            continue
            
        outpost = rep_service.get_outpost(outpost_id)
        if outpost:
            # Base weight from tier
            base_weight = outpost.tier.voting_weight
            
            # Gravity Bonus: high-gravity history increases influence
            gravity_bonus = 0.0
            pulse_count = getattr(outpost, "pulse_count", 0)
            cumulative_gravity = getattr(outpost, "cumulative_gravity", 0.0)
            if pulse_count > 0:
                avg_gravity = cumulative_gravity / pulse_count
                gravity_bonus = min(0.5, avg_gravity / 100.0) # Cap bonus at 0.5
                
            total_weight += base_weight + gravity_bonus
            external_sigs += 1
            
    # Apply Source Multiplier (Epistemic Firewall)
    source_url = entry.get("metadata", {}).get("source_url", "")
    source_multiplier = source_validator.get_multiplier(source_url)
    
    final_weight = round(total_weight * source_multiplier, 2)
    
    # The 'Triangulation Floor': Even with high weight, we demand at least 2 external signers for verification
    if external_sigs < 2:
        logger.debug(f"Consensus: Waiting for external triangulation (Sigs: {external_sigs}) for {entry['id']}")
        # We return the calculated weight but the controller should check external_sigs >= 2
    
    logger.debug(f"Calculated external consensus for {entry['id']}: {final_weight} (Ext Sigs: {external_sigs}, Multiplier: {source_multiplier}x)")
    return final_weight


def create_genesis_entry(identity: OutpostIdentity) -> dict[str, Any]:
    """Create the Genesis entry - the first entry in The Chronicle.

    This entry records the birth of this Probe and its first Intelligence Perimeter.

    Args:
        identity: The Probe's sovereign identity.

    Returns:
        A sealed Genesis entry.
    """
    data = {
        "type": "GenesisEntry",
        "title": "The Chronicle Probe Initialization",
        "description": (
            "This Probe has been initialized as a sovereign participant "
            "in the Discovery Mesh."
        ),
        "intelligence_perimeter": ["Meta Infrastructure", "LEAP District"],
        "outpost_alias": "Probe 0x0001",
    }

    return create_entry(
        identity=identity,
        data=data,
        source_url="local://identity-bootstrap",
        probe_id="genesis",
        status="verified",
    )
