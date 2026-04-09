#!/usr/bin/env python3
"""
The Chronicle - Network Mechanism Module

Implements the MeshClient for communication with the Bridge Server.
"""

import httpx
import os
import logging
from typing import Any, Optional, Dict, List

logger = logging.getLogger(__name__)

class MeshClient:
    """Sovereign client for the Discovery Mesh Bridge API."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0):
        """Initialize the Mesh Client.

        Args:
            base_url: The Bridge Server URL. Defaults to BRIDGE_URL env var.
            timeout: Default timeout for network operations.
        """
        self.base_url = base_url or os.getenv("BRIDGE_URL", "http://localhost:4110")
        self.timeout = timeout
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """Close the underlying HTTP client."""
        self._client.close()

    def get_status(self) -> Dict[str, Any]:
        """Fetch the current bridge status and heartbeat state."""
        response = self._client.get("/status")
        response.raise_for_status()
        return response.json()

    def submit_pulse(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a new pulse to the Ledger for verification.

        Args:
            entry: A complete, sealed Ledger entry.

        Returns:
            The API response JSON.
        """
        response = self._client.post("/chronicle", json=entry)
        response.raise_for_status()
        return response.json()

    def sign_entry(self, cid: str, outpost_id: str) -> Dict[str, Any]:
        """Contribute a sovereign signature to an existing entry.

        Args:
            cid: The Content Identifier of the entry.
            outpost_id: The ID of the signing outpost.

        Returns:
            The API response JSON (updated weight and status).
        """
        payload = {"cid": cid, "outpost_id": outpost_id}
        response = self._client.post("/chronicle/sign", json=payload)
        response.raise_for_status()
        return response.json()

    def claim_inquiry(self, handshake: Dict[str, Any]) -> Dict[str, Any]:
        """Claim an open Truth Seeker inquiry with a signed handshake."""
        response = self._client.post("/inquiries/claim", json=handshake)
        response.raise_for_status()
        return response.json()

    def complete_inquiry(self, proof: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a signed Proof of Discovery for settlement."""
        response = self._client.post("/inquiries/complete", json=proof)
        response.raise_for_status()
        return response.json()

    def get_inquiries(self) -> List[Dict[str, Any]]:
        """List all open inquiries from the Bridge Server."""
        response = self._client.get("/inquiries")
        response.raise_for_status()
        return response.json()

    def get_snapshot(self, outpost_id: str, signature: str) -> bytes:
        """Request a full Granary snapshot (Mirror).

        Args:
            outpost_id: The ID of the requesting outpost.
            signature: A signature of "REQUEST_SNAPSHOT" by the outpost.

        Returns:
            The raw snapshot bytes (Vault file).
        """
        payload = {"outpost_id": outpost_id, "signature": signature}
        response = self._client.post("/vault/snapshot", json=payload)
        response.raise_for_status()
        return response.content
