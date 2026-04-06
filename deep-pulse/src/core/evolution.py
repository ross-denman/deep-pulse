#!/usr/bin/env python3
"""
Deep Pulse — Evolution Engine

The self-improving 'Flywheel' of the swarm.
Monitors scout success, extracts effective patterns, and proposes library updates.
"""

import logging
import json
import os
import yaml
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class EvolutionEngine:
    """The engine that manages the Discovery-to-Tool pipeline."""

    def __init__(self, node_id: str, memory_client, library_path: str = "library/"):
        self.node_id = node_id
        self.memory = memory_client
        self.library_path = library_path

    async def scout_success_audit(self) -> List[Dict[str, Any]]:
        """
        Monitors RLM memory for high-reward discovery paths.
        Identifies successful query patterns and target structures.
        """
        logger.info("Auditing successful discovery paths...")
        candidates = self.memory.get_audit_candidates(min_reward=0.8)
        logger.info(f"Evolution Engine: Found {len(candidates)} candidates for library promotion.")
        return candidates

    async def library_proposal_gen(self, episode: Dict[str, Any]) -> str:
        """
        Converts a successful episode into a machine-readable YAML template.
        """
        p_id = f"evolved_{episode['perimeter']}_{episode['id']}"
        logger.info(f"Generating library proposal: {p_id}")
        
        path = json.loads(episode['path_json'])
        metadata = json.loads(episode['metadata_json'] or "{}")
        
        # Extract the final successful URL and keywords
        target_url = next((step['params']['url'] for step in path if 'params' in step and 'url' in step['params']), "unknown")
        keywords = next((step['params']['keywords'] for step in path if 'params' in step and 'keywords' in step['params']), [])

        perimeter_data = {
            "id": p_id,
            "name": f"Evolved Perimeter: {episode['perimeter']}",
            "description": f"Automatically evolved from successful discovery {episode['id']} on {target_url}.",
            "node_origin": self.node_id,
            "keywords": keywords,
            "targets": [{"url": target_url, "type": "portal"}],
            "selectors": metadata.get("selectors", {}),
            "recursive_depth": 3,
            "adaptive_rag": True,
            "evolved": True
        }

        os.makedirs(os.path.join(self.library_path, "perimeters"), exist_ok=True)
        yaml_path = os.path.join(self.library_path, "perimeters", f"{p_id}.yaml")
        
        with open(yaml_path, "w") as f:
            yaml.dump(perimeter_data, f, sort_keys=False)

        logger.info(f"✅ Library Proposal Generated: {yaml_path}")
        return yaml_path

    async def run_flywheel(self):
        """Executes the full audit-to-proposal pipeline."""
        candidates = await self.scout_success_audit()
        proposals = []
        for cand in candidates:
            # Check if we already evolved this
            proposal = await self.library_proposal_gen(cand)
            proposals.append(proposal)
        return proposals
