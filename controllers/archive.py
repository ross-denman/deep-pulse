#!/usr/bin/env python3
"""
Deep Ledger - Archive Controller (Policy Layer)

Handles the synchronization of the immutable chronicle with the Knowledge Graph (KÃƒÂ¹zuDB/Neo4j).
Manages the Resurrection Layer (rebuild) and snapshot exports.
"""

import logging
import asyncio
import subprocess
import sys
from datetime import datetime
from typing import List, Dict, Any, Tuple
from pathlib import Path

# We import these for the mapping logic
try:
    from core.chronicle import read_ledger, verify_entry
    from agents.auditor import ExtractedEntity, ScoutResult, LEAPDistrictIntel
except ImportError:
    # Handle environment where agents module isn't on path
    from core.models import ExtractedEntity, ScoutResult, LEAPDistrictIntel
    from core.chronicle import read_ledger, verify_entry

# Hybrid Sovereignty: Default to KuzuDB for Outposts, Neo4j for Notaries
try:
    from core.kuzu_driver import KuzuDriver as GraphDriver
except ImportError:
    try:
        from core.graph_driver import GraphDriver
    except ImportError:
        GraphDriver = None

logger = logging.getLogger(__name__)

class ArchiveController:
    """Orchestrates ledger-to-graph synchronization and chronicle maintenance."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def get_recent_entries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch the latest entries from the chronicle."""
        try:
            ledger = read_ledger()
            return ledger[-limit:] if limit > 0 else ledger
        except Exception as e:
            logger.error(f"Failed to read ledger: {e}")
            return []

    async def sync_to_graph(self) -> Tuple[int, int, int]:
        """Synchronize the Public Chronicle with the Neo4j Knowledge Graph.
        
        Returns:
            Tuple: (synced_count, verified_count, total_count)
        """
        if not GraphDriver:
            logger.error("Neo4j GraphDriver not available.")
            return 0, 0, 0

        ledger = read_ledger()
        synced = 0
        verified = 0
        
        async with GraphDriver() as driver:
            if not driver.is_connected:
                logger.error("Neo4j offline. Sync aborted.")
                return 0, 0, len(ledger)

            for entry in ledger:
                # 1. Verify integrity before ingestion
                if not verify_entry(entry):
                    continue
                verified += 1
                
                cid = entry["id"]
                data = entry["data"]
                meta = entry["metadata"]
                
                # 2. Heuristic Mapping for Intelligence Ingestion
                entities = self._map_entry_to_entities(data)
                
                dummy_intel = LEAPDistrictIntel(
                    title=data.get("title") or entry["id"][:20],
                    target_id=meta.get("probe_id", "sync"),
                    keyword_hit_count=0,
                    total_keywords=0,
                    content_length=0,
                    perimeter=data.get("intelligence_perimeter", ["General Intelligence"])[0] 
                    if isinstance(data.get("intelligence_perimeter"), list) else "General Intelligence"
                )
                
                res = ScoutResult(
                    scout_id=meta.get("probe_id", "sync"),
                    source_url=meta.get("source_url", "local://sync"),
                    timestamp=datetime.fromisoformat(meta["timestamp"].replace("Z", "+00:00")),
                    intel=dummy_intel,
                    entities=entities,
                    relationships=[]
                )
                
                # 3. Ingest into Neo4j
                stats = await driver.ingest_scout_result(res, cid, entry["proof"]["signature"])
                if stats["entry_merged"]:
                    synced += 1

        return synced, verified, len(ledger)

    def trigger_resurrection(self) -> Tuple[bool, str]:
        """Trigger the Resurrection Layer to rebuild the Knowledge Graph from scratch."""
        rebuild_script = str(self.project_root / "src" / "db" / "rebuild_graph.py")
        
        try:
            result = subprocess.run([sys.executable, rebuild_script], capture_output=True, text=True)
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
        except Exception as e:
            return False, str(e)

    def _map_entry_to_entities(self, data: Dict[str, Any]) -> List[Any]:
        """Heuristic mapping logic moved from bridge.py."""
        entities = []
        
        # Genesis Mapping
        if data.get("type") == "GenesisEntry":
            entities.append(ExtractedEntity(name="The Public Chronicle", entity_type="Project", description="Immutable infrastructure"))
            entities.append(ExtractedEntity(name="Outpost 0x0001", entity_type="Organization", description="Sovereign outpost"))
        
        # Intelligence Mapping (Ozempic/AAOS/Lutnick heuristics)
        elif data.get("type") == "TruthPulse":
            insight = data.get("insight", {})
            claim_keyword = insight.get("claim_keyword", "")
            source = insight.get("source", "")
            
            if "Ozempic" in claim_keyword:
                entities.append(ExtractedEntity(name="Ozempic", entity_type="Resource", description="Weight loss drug subject to audit"))
                entities.append(ExtractedEntity(name="AAOS", entity_type="Agency", description="Medical study source"))
            if "Lutnick" in source:
                entities.append(ExtractedEntity(name="Secretary Lutnick", entity_type="Person", description="Department of Commerce"))
            if "Panama Canal" in source:
                entities.append(ExtractedEntity(name="Panama Canal", entity_type="Location", description="Global logistics nexus"))
                
        return entities
