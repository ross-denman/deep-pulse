import subprocess
import json
import logging
import time
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT / "src" / "public"))

try:
    from src.public.probes.library.manager import ProbeManager
    from src.public.core.identity import load_identity
except ImportError:
    # Handle direct execution or alternative path structures
    sys.path.append(str(PROJECT_ROOT / "src" / "public" / "probes" / "library"))
    try:
        from manager import ProbeManager
    except ImportError:
        # Fallback to current relative path if inside probes folder
        sys.path.append(str(Path(__file__).resolve().parent / "library"))
        from manager import ProbeManager
    from src.public.core.identity import load_identity

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bloodhound_sower")

def get_initial_seeds():
    """Pulls initial investigative targets from profile or default seeding."""
    # Mocking initial seeds for now. In production, this pulls from discovery_profile.json
    return [
        {"type": "url", "value": "https://github.com/vinta/awesome-python"}, # Example awesome list
        {"type": "company", "value": "Meta LEAP Lebanon"} # Focused investigative target
    ]

def run_sower_pass(seed_entities: list = None):
    """Executes the Multi-Stage Investigative Pipeline."""
    logger.info("📡 [BLOODHOUND SOWER] 📡 Initiating Recursive Pipeline...")
    
    try:
        identity = load_identity()
    except Exception as e:
        logger.error(f"Identity failure: {e}")
        return

    # 1. Initialize Manager (Dynamic Discovery)
    manager = ProbeManager(outpost_id=identity.outpost_id)
    manager.load_all()
    
    # 2. Identify Initial Seeds
    if not seed_entities:
        seed_entities = get_initial_seeds()
        
    if not seed_entities:
        logger.warning("No seeds found. Aborting.")
        return

    # 3. Trigger the Recursive Pipeline (The Engine)
    # The Governor is set to 3 by default as per Sprint 06 standards.
    manager.run_pipeline(seed_entities, max_depth=3)

if __name__ == "__main__":
    # Perform one full pass. In OCI deployment, this would be cron-driven or run in-loop.
    run_sower_pass()
