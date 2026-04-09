#!/usr/bin/env python3
"""
Deep Ledger - Discovery Vault (Storage Mechanism)

Handles the local persistence of inquiry claims and discovery state.
Ensures that outposts do not repeat work and maintain an audit trail of actions.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class DiscoveryVault:
    """Persistent storage for discovery state and inquiry claims."""

    def __init__(self, storage_path: Path):
        """Initialize the Discovery Vault.

        Args:
            storage_path: Path to the JSON storage file.
        """
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load data from the storage file."""
        if not self.storage_path.exists():
            return {"claims": {}, "metadata": {"version": "1.0"}}
        
        try:
            with open(self.storage_path, "r") as f:
                content = f.read().strip()
                if not content:
                    return {"claims": {}, "metadata": {"version": "1.0"}}
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load Discovery Vault: {e}")
            return {"claims": {}, "metadata": {"version": "1.0"}}

    def save(self) -> None:
        """Persist the current state to disk."""
        try:
            with open(self.storage_path, "w") as f:
                json.dump(self._data, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save Discovery Vault: {e}")

    def save_claim(self, inquiry_id: str, metadata: Dict[str, Any]) -> None:
        """Record a new inquiry claim.

        Args:
            inquiry_id: The unique ID of the inquiry.
            metadata: Additional info (timestamp, lease_expiry, etc).
        """
        self._data["claims"][inquiry_id] = metadata
        self.save()

    def get_claim(self, inquiry_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a claim record by ID."""
        return self._data["claims"].get(inquiry_id)

    def is_claimed(self, inquiry_id: str) -> bool:
        """Check if an inquiry has already been claimed locally."""
        return inquiry_id in self._data["claims"]

    def list_claims(self) -> Dict[str, Any]:
        """Return all local claims."""
        return self._data["claims"]

    def clear_claims(self) -> None:
        """Reset all claim records."""
        self._data["claims"] = {}
        self.save()
