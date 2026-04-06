#!/usr/bin/env python3
"""
Deep Pulse — Agent Manager (Tool Procurement)

Primary Orchestration layer that maps incoming signals to the correct
OSINT sensors and APIs based on the global Ontology.
"""

import logging
import yaml
import os
import json
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class AgentManager:
    """
    Coordinates tool discovery and scout tasking.
    Handles 'Procurement' by mapping signals to sensors (ADS-B, EPA, USGS, etc.).
    """

    def __init__(self, ontology_path: str = "library/ontology.yaml"):
        self.ontology_path = ontology_path
        self.ontology = self._load_ontology()
        self.active_missions = {}

    def _load_ontology(self) -> Dict[str, Any]:
        """Loads the global ontology map."""
        if not os.path.exists(self.ontology_path):
            logger.error(f"Ontology file NOT FOUND at {self.ontology_path}")
            return {"categories": []}
        
        try:
            with open(self.ontology_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to parse ontology: {e}")
            return {"categories": []}

    def procure_tool(self, signal_keywords: List[str]) -> Optional[Dict[str, Any]]:
        """
        Maps signal keywords to the correct Category, Trigger, and Sensor.
        """
        signal_lower = [k.lower() for k in signal_keywords]
        
        for category in self.ontology.get("categories", []):
            keywords = [k.lower() for k in category.get("keywords", [])]
            # Intersection: do we have a match?
            if any(k in signal_lower for k in keywords):
                logger.info(f"Agent Manager: Mapped signal to Category Trigger: {category.get('trigger')}")
                return category
                
        logger.warning(f"Agent Manager: No tool in ontology matches keywords: {signal_keywords}")
        return None

    async def task_scout(self, mission_id: str, target_data: Dict[str, Any], scout_class):
        """
        Hooks into the scout execution loop.
        """
        logger.info(f"Agent Manager: Tasking scout for mission {mission_id} on target {target_data.get('name')}")
        # Scout logic triggered here.
        # This will interface with the Architect Swarm if the target_data is 'blank' or 'obsolete'.
        pass

    def get_environmental_status(self) -> Dict[str, Any]:
        """Summarizes current monitoring coverage."""
        return {
            "sectors": [c.get("trigger") for c in self.ontology.get("categories", [])],
            "total_sensors": len(self.ontology.get("categories", []))
        }

    def handle_schema_drift(
        self,
        target_url: str,
        old_field: str,
        new_field: str,
        confidence: float,
        source_name: str = ""
    ) -> bool:
        """
        Orchestrates the Schema Drift approval workflow.
        Detection -> Reporter Gate -> Architect Persistence.
        Returns True if the update was approved and persisted.
        """
        from src.orchestration.reporter import ReporterAgent
        from src.architects.lead_manager import LeadArchitect

        reporter = ReporterAgent()
        architect = LeadArchitect()

        source = source_name or target_url
        yaml_path = f"templates/perimeters/{source.lower().replace(' ', '_')}.yaml"

        approved = reporter.request_schema_approval(
            source_name=source,
            old_field=old_field,
            new_field=new_field,
            confidence=confidence,
            yaml_path=yaml_path
        )

        if approved:
            blueprint = {"schema_update": {"old": old_field, "new": new_field, "confidence": confidence}}
            architect.persist_blueprint(source.lower().replace(" ", "_"), blueprint)
            logger.info(f"Agent Manager: Schema drift resolved for {source}.")
        else:
            logger.info(f"Agent Manager: Schema drift DENIED by operator for {source}.")
        
        return approved

    def debrief_scout(self, mission_id: str, summary: Dict[str, Any], session_cost: float = 0.0):
        """
        Parses the scout's debrief summary and updates Global Heuristics.
        Implements the 'Dream-to-Data' Feedback Loop.
        """
        logger.info(f"Agent Manager: Starting Mission Debrief for '{mission_id}'...")
        
        # 1. Update Global Heuristics Ledger (RLM Memory)
        heuristics_path = "data/heuristics/global_ledger.yaml"
        os.makedirs("data/heuristics", exist_ok=True)
        
        ledger = {}
        if os.path.exists(heuristics_path):
            try:
                with open(heuristics_path, "r") as f:
                    ledger = yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Failed to read ledger: {e}")
        
        updates = summary.get("heuristics_update", {})
        
        # Merge Avoid Paths (Blacklist/Skipping)
        avoid = set(ledger.get("avoid_paths", []))
        avoid.update(updates.get("avoid_paths", []))
        ledger["avoid_paths"] = list(avoid)
        
        # Merge Preferred Paths (Pattern Recognition)
        preferred = set(ledger.get("preferred_paths", []))
        preferred.update(updates.get("preferred_paths", []))
        ledger["preferred_paths"] = list(preferred)
        
        try:
            with open(heuristics_path, "w") as f:
                yaml.dump(ledger, f, sort_keys=False)
        except Exception as e:
            logger.error(f"Failed to save ledger: {e}")
            
        # 2. Update Perimeter Config with "Preferred Paths"
        perimeter_path = f"templates/perimeters/{mission_id}.yaml"
        if os.path.exists(perimeter_path):
            try:
                with open(perimeter_path, "r") as f:
                    p_config = yaml.safe_load(f)
                
                new_sources = summary.get("new_potential_sources", [])
                if new_sources:
                    targets = p_config.get("targets", [])
                    existing_urls = {t.get('url') for t in targets}
                    
                    added_count = 0
                    for url in new_sources:
                        if url not in existing_urls:
                            targets.append({"url": url, "type": "verified_discovery"})
                            added_count += 1
                    
                    if added_count > 0:
                        p_config["targets"] = targets
                        with open(perimeter_path, "w") as f:
                            yaml.dump(p_config, f, sort_keys=False)
                        logger.info(f"Agent Manager: Added {added_count} new sources to {mission_id}.yaml")
            except Exception as e:
                logger.error(f"Failed to update perimeter config: {e}")
            
        # 3. Log total cost against budget
        logger.info(f"Agent Manager: Mission {mission_id} complete. Cost: ${session_cost:.4f}")
        
        print(f"\n  {C.GREEN}✅ Mission Debrief Complete: '{mission_id}'{C.RESET}")
        print(f"  {C.DIM}Heuristics: {len(ledger.get('avoid_paths', []))} blacklisted, {len(ledger.get('preferred_paths', []))} preferred.{C.RESET}")

class C:
    """Terminal colors."""
    GREEN = '\033[92m'
    CYAN = '\033[96m'
    DIM = '\033[2m'
    RESET = '\033[0m'
