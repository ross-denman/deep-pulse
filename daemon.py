import asyncio
import logging
import os
import signal
import sys
from pathlib import Path
from datetime import datetime, timezone

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src" / "public"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.public.controllers.hunt import HuntController
from src.public.storage.queue import InquiryQueue
from src.public.scouts.templates.web_scout import WebScout
from src.public.core.network import MeshClient
from src.public.core.identity import load_identity
from src.public.storage.vault import DiscoveryVault

# Setup logging
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "nexus_daemon.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("nexus_daemon")

# --- Manager Stubs to satisfy BaseScout requirements ---
class StubConfig:
    def __init__(self, use_proxy=False):
        self.use_proxy = use_proxy
        self.proxy_url = os.getenv("TOR_PROXY", "socks5://127.0.0.1:9050")
        self.strict_proxy = False
    def get_best_distiller(self):
        return {"type": "local", "model": os.getenv("OLLAMA_MODEL", "llama3"), "base_url": os.getenv("OLLAMA_URL", "http://localhost:11434/v1")}
    def check_compute_budget(self, cost, elapsed):
        return True

class StubEconomy:
    def spend_credit(self):
        return True

class StubMemory:
    def record_episode(self, perimeter, meta): return 1
    def update_path(self, ep_id, action): pass
    def update_reward(self, ep_id, reward): pass
    def save_successful_metadata(self, ep_id, meta): pass

class NexusDaemon:
    def __init__(self, interval_minutes: int = 45):
        self.interval = interval_minutes * 60
        self.running = True
        
        # Initialize dependencies
        self.queue = InquiryQueue()
        self.identity = load_identity()
        self.vault = DiscoveryVault(PROJECT_ROOT / "harvest" / "discovery_vault.json")
        self.client = MeshClient()
        
        # Configure WebScout with stubs
        self.scout = WebScout(
            perimeter="DAEMON_AUTO_HUNT",
            config_manager=StubConfig(use_proxy=False),
            economy_manager=StubEconomy(),
            memory_manager=StubMemory()
        )
        
        self.hunt_controller = HuntController(self.queue, self.scout)

    def stop(self, *args):
        logger.info("Shutdown signal received. Nexus Daemon powering down...")
        self.running = False

    async def run(self):
        logger.info("=== NEXUS DAEMON POSSESSED ===")
        logger.info(f"Interval: {self.interval // 60} minutes (Brave Quota Protection)")
        
        while self.running:
            try:
                # ─── Quota Guard ───
                search_client = self.hunt_controller.search_client
                usage = search_client.get_usage_percent()
                low_volume_mode = usage > 90.0
                
                if low_volume_mode:
                    logger.warning(f"⚠️ QUOTA GUARD: Usage at {usage:.1f}%. Activating Passive Notary mode.")
                
                logger.info("Pulse check: Scanning Master Outpost Queue...")
                seeds = self.queue.list_open_inquiries()
                queued = [s for s in seeds if s['status'] == 'QUEUED']
                
                if not queued:
                    logger.info("No queued targets. Resting...")
                else:
                    top_seed = queued[0]
                    gravity = top_seed.get("gravity", 0.0)
                    
                    # Fallback logic: Skip non-urgent seeds if in low volume mode
                    if low_volume_mode and gravity < 10.0:
                        logger.info(f"Passive Mode: Skipping '{top_seed['title']}' (Gravity {gravity} < 10.0) due to search quota.")
                    else:
                        processed = await self.hunt_controller.process_seed(top_seed['id'])
                        if processed:
                            logger.info(f"Cycle complete. Distilled: {top_seed['title']}")

            except Exception as e:
                logger.error(f"Daemon Cycle Error: {e}")

            if not self.running:
                break
                
            logger.info(f"Sleeping for {self.interval // 60}m...")
            await asyncio.sleep(self.interval)

if __name__ == "__main__":
    daemon = NexusDaemon()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, daemon.stop)
    signal.signal(signal.SIGTERM, daemon.stop)
    
    asyncio.run(daemon.run())
