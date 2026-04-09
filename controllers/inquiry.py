#!/usr/bin/env python3
"""
Deep Ledger - Inquiry Controller (Policy Layer)

Orchestrates the lifecycle of an inquiry: Discovery -> Claim -> Evidence -> Submission.
Acts as a high-level bridge between the CLI interface and low-level mechanisms.
"""

import logging
from typing import Any, Dict, List, Optional

from src.public.core.network import MeshClient
from src.public.core.identity import OutpostIdentity
from src.public.core.chronicle import create_entry
from src.public.core.sources import source_validator
from src.public.storage.vault import DiscoveryVault
from src.public.core.contracts import ClaimHandshake, ProofOfDiscovery
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

class InquiryController:
    """Orchestrates the lifecycle of Truth Seeker inquiries."""

    def __init__(self, client: MeshClient, identity: OutpostIdentity, vault: DiscoveryVault):
        """Initialize the Inquiry Controller.

        Args:
            client: The MeshClient for network communication.
            identity: The OutpostIdentity for signing.
            vault: The DiscoveryVault for persistence.
        """
        self.client = client
        self.identity = identity
        self.vault = vault

    async def get_active_inquiries(self) -> List[Dict[str, Any]]:
        """Retrieve enqueued Truth Seeds from the local MasterOutpostQueue."""
        try:
            from src.private.master_queue import MasterOutpostQueue
            queue = MasterOutpostQueue()
            return queue.list_open_inquiries()
        except Exception as e:
            logger.error(f"Failed to retrieve active inquiries: {e}")
            return []

    def sync_mesh(self) -> List[Dict[str, Any]]:
        """Fetch all available inquiries from the Discovery Mesh.

        Returns:
            A list of inquiry records.
        """
        try:
            inquiries = self.client.get_inquiries()
            logger.info(f"Sync complete. Found {len(inquiries)} inquiries.")
            return inquiries
        except Exception as e:
            logger.error(f"Failed to sync mesh inquiries: {e}")
            return []

    def claim_inquiry(self, inquiry_id: str) -> Optional[Dict[str, Any]]:
        """Claim a specific inquiry to prevent double-work.

        Args:
            inquiry_id: The ID of the inquiry to claim.

        Returns:
            The claim status metadata if successful, else None.
        """
        if self.vault.is_claimed(inquiry_id):
            logger.info(f"Inquiry {inquiry_id} already claimed locally.")
            return self.vault.get_claim(inquiry_id)

        try:
            logger.info(f"Claiming inquiry {inquiry_id} with signed handshake...")
            
            # Create Signed Handshake
            handshake = ClaimHandshake(
                inquiry_id=inquiry_id,
                outpost_id=self.identity.outpost_id,
                timestamp=datetime.now(timezone.utc)
            )
            signing_payload = f"{handshake.inquiry_id}{handshake.outpost_id}{handshake.timestamp.isoformat()}"
            handshake.signature = self.identity.sign(signing_payload.encode())
            
            claim_res = self.client.claim_inquiry(handshake.model_dump(mode="json"))
            
            # Persist the claim locally
            self.vault.save_claim(inquiry_id, claim_res)
            logger.info(f"Successfully claimed inquiry {inquiry_id}.")
            return claim_res
        except Exception as e:
            logger.error(f"Failed to claim inquiry {inquiry_id}: {e}")
            return None

    def submit_evidence(self, inquiry_id: str, payload: Dict[str, Any], source_url: str) -> Optional[Dict[str, Any]]:
        """Submit evidence/findings for a claimed inquiry."""
        if not self.vault.is_claimed(inquiry_id):
            logger.warning(f"Attempting to submit evidence for unclaimed inquiry: {inquiry_id}")

        try:
            logger.info(f"Notarizing evidence for inquiry {inquiry_id}...")
            # Epistemic Firewall: Multi-Stage Weighting
            is_volatile = source_validator.is_volatile(source_url)
            status = "volatile" if is_volatile else "speculative"
            
            entry = create_entry(
                identity=self.identity,
                data=payload,
                source_url=source_url,
                probe_id=f"inquiry:{inquiry_id}",
                status=status
            )

            # Rebrand as ProofOfDiscovery (Sealed Audit Package)
            claim_data = self.vault.get_claim(inquiry_id)
            if not claim_data:
                 raise ValueError("Original claim metadata not found in vault.")
            
            handshake = ClaimHandshake(**claim_data) # Reconstruct from vault
            
            proof = ProofOfDiscovery(
                grain_id=entry["id"],
                payload=entry,
                handshake=handshake
            )

            logger.info(f"Submitting Proof of Discovery for {inquiry_id} to Notary...")
            return self.client.complete_inquiry(proof.model_dump(mode="json"))
        except Exception as e:
            logger.error(f"Failed to submit evidence for inquiry {inquiry_id}: {e}")
            return None

    def get_mesh_state(self) -> Dict[str, Any]:
        """Aggregate the state of the P2P Discovery Mesh (Simulation)."""
        try:
            from src.public.core.p2p import P2PManager
            p2p = P2PManager()
            return {
                "outpost_id": p2p.identity.outpost_id,
                "port": p2p.port,
                "peers": p2p.outposts,
                "known_cids": len(p2p.known_cids)
            }
        except ImportError:
            return {"peers": {}, "known_cids": 0}

    async def sync_mesh_discovery(self) -> int:
        """Synchronize with discovered peers to reconcile mesh state."""
        try:
            from src.public.core.p2p import P2PManager
            p2p = P2PManager()
            p2p._load_outposts()
            p2p._refresh_cid_cache()
            
            count = 0
            for peer in p2p.outposts.values():
                try:
                    await p2p.request_sync_from_outpost(peer)
                    count += 1
                except Exception:
                    continue
            return count
        except ImportError:
            return 0

    async def process_heartbeat(self, interval: int = 30):
        """Maintain the OCI Heartbeat (maintain_gravity) link."""
        try:
            from src.public.core.heartbeat import HeartbeatManager
            manager = HeartbeatManager(interval_minutes=interval)
            logger.info(f"Heartbeat activated (interval: {interval}m)")
            await manager.run_forever()
        except Exception as e:
            logger.error(f"Heartbeat failure: {e}")
            raise
