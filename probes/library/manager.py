import importlib
import pkgutil
import logging
import sys
import os
from pathlib import Path
from typing import List, Type, Dict

# Ensure local imports work during dynamic loading
LIBRARY_ROOT = Path(__file__).resolve().parent
if str(LIBRARY_ROOT) not in sys.path:
    sys.path.append(str(LIBRARY_ROOT))

try:
    from base_probe import BaseCuriosityProbe
except ImportError:
    from .base_probe import BaseCuriosityProbe

logger = logging.getLogger("probe_manager")

class ProbeManager:
    """
    The Specialized Brain of the Discovery Mesh.
    Modularized discovery engine for categorized Curiosity Probes.
    """
    def __init__(self, outpost_id: str, bridge_url: str = "http://localhost:4110"):
        self.outpost_id = outpost_id
        self.bridge_url = bridge_url
        self.library_path = LIBRARY_ROOT
        self.registry: Dict[str, Type[BaseCuriosityProbe]] = {}
        self.loaded_probes: List[BaseCuriosityProbe] = []
        self._discover_plugins()

    def _discover_plugins(self):
        """Recursively scan library categories and load probe classes."""
        logger.info(f"[SRCH] [SCANNING LIBRARY] {self.library_path}")
        
        # Standard Categorical Hierarchy
        categories = ["surface", "deep", "logic", "forensic"]
        
        for category in categories:
            cat_path = self.library_path / category
            if not cat_path.exists():
                cat_path.mkdir(parents=True, exist_ok=True)
                continue
                
            # Use pkgutil to walk the directory for modules
            # prefix category name for correct import path
            for loader, module_name, is_pkg in pkgutil.walk_packages([str(cat_path)], prefix=f"{category}."):
                try:
                    # Clear cache if re-scanning (for future Hot-Loading)
                    if module_name in sys.modules:
                        importlib.reload(sys.modules[module_name])
                        
                    module = importlib.import_module(module_name)
                    
                    # Find all classes that inherit from BaseCuriosityProbe
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, BaseCuriosityProbe) and 
                            attr is not BaseCuriosityProbe):
                            
                            logger.info(f"[*] [PLUGIN REGISTERED] {category}/{attr_name}")
                            self.registry[f"{category}.{attr_name}"] = attr
                except Exception as e:
                    logger.error(f"Failed to load plugin {module_name}: {e}")

    def load_all(self, refresh: bool = False) -> List[BaseCuriosityProbe]:
        """Instantiates all registered probes. Set refresh=True to re-scan library."""
        if refresh:
            self.registry = {}
            self._discover_plugins()
            
        self.loaded_probes = []
        for name, cls in self.registry.items():
            try:
                probe = cls(outpost_id=self.outpost_id, bridge_url=self.bridge_url)
                self.loaded_probes.append(probe)
            except Exception as e:
                logger.error(f"Failed to instantiate {name}: {e}")
        return self.loaded_probes

    def get_probes_for_type(self, entity_type: str) -> List[BaseCuriosityProbe]:
        """Returns probes that accept the given entity_type as input."""
        return [p for p in self.loaded_probes if entity_type in getattr(p, "input_types", [])]

    def run_pipeline(self, initial_entities: List[Dict], max_depth: int = 3):
        """
        The Multi-Stage Investigative Pipeline.
        Triggers probes recursively based on entity-type matching.
        """
        logger.info(f"[SYNC] [PIPELINE START] Seeded with {len(initial_entities)} entities. Governor: {max_depth}")
        if not self.loaded_probes:
            self.load_all()
        self._execute_recursive(initial_entities, depth=1, max_depth=max_depth)

    def _execute_recursive(self, entities: List[Dict], depth: int, max_depth: int):
        """Internal recursive loop for Data-Triggered Execution."""
        if depth > max_depth:
            logger.info(f"[HALT] [GOVERNOR] Max depth {max_depth} reached. Halting recursion.")
            return

        next_tier_entities = []
        for entity in entities:
            etype = entity.get("type")
            evalue = entity.get("value")
            if not etype:
                continue

            matched_probes = self.get_probes_for_type(etype)
            for probe in matched_probes:
                logger.info(f"[DPT] [DEPTH {depth}] {probe.category}/{probe.name} triggered by {etype}:{evalue}")
                try:
                    # 1. Harvest Chaff (with seed)
                    chaff = probe.harvest(seed=entity)
                    if not chaff:
                        continue

                    # 2. Sift for Grains (findings)
                    grains = probe.sift(chaff)
                    if not grains:
                        continue

                    logger.info(f"   [*] {probe.probe_id}: Found {len(grains)} divergent entries.")
                    
                    for grain in grains:
                        # 3. Settle Locally (Notarize & Seal)
                        if probe.settle(grain):
                            # Successful settlement check. In a real scenario, this would contact bridge.py
                            # For the pipeline, we extract discovered entities for the next tier
                            discovered = grain.get("entities", [])
                            next_tier_entities.extend(discovered)
                            
                except Exception as e:
                    logger.error(f"[ERR] Pipeline error in {probe.name} at depth {depth}: {e}")

        if next_tier_entities:
            # Deduplicate next tier entities to prevent redundant work
            unique_keys = set()
            dedup_entities = []
            for e in next_tier_entities:
                key = f"{e.get('type')}:{e.get('value')}"
                if key not in unique_keys:
                    unique_keys.add(key)
                    dedup_entities.append(e)
            
            logger.info(f"[TIER] [NEXT TIER] Depth {depth} produced {len(dedup_entities)} unique seeds for Tier {depth + 1}.")
            self._execute_recursive(dedup_entities, depth + 1, max_depth)

if __name__ == "__main__":
    # Test script for library scanning
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    
    # Try to resolve identity for test instance
    try:
        sys.path.append(str(LIBRARY_ROOT.parent.parent))
        from core.identity import load_identity
        identity = load_identity()
        outpost_id = identity.outpost_id
    except:
        outpost_id = "TEST_OUTPOST"

    manager = ProbeManager(outpost_id=outpost_id)
    probes = manager.load_all()
    
    print(f"\n--- Probe Registry ({len(probes)} active) ---")
    for p in probes:
        print(f"[{p.category}] {p.name} (ID: {p.probe_id})")
    print("---------------------------------\n")
