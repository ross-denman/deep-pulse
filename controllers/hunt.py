import logging
import asyncio
import json
from typing import Dict, Any, List
from core.search import BraveSearchClient
from scouts.templates.web_scout import WebScout
from private.master_queue import MasterOutpostQueue
from core.models import PeriodicalBrief

logger = logging.getLogger("hunt_controller")

class HuntController:
    """
    Coordinates Discovery (Brave Search) and Harvesting (Crawl4AI).
    Bridges the gap between a Truth Seed and a distilled Finding.
    """
    def __init__(self, queue: MasterOutpostQueue, scout: WebScout):
        self.queue = queue
        self.scout = scout
        self.search_client = BraveSearchClient()

    async def process_seed(self, seed_id: str) -> bool:
        """
        Processes a single seed from the MasterOutpostQueue.
        1. Search for authoritative links.
        2. Scrape top results.
        3. Distill and submit findings.
        """
        # Fetch the seed
        seeds = self.queue.list_open_inquiries()
        seed = next((s for s in seeds if s['id'] == seed_id), None)
        
        if not seed:
            logger.error(f"Seed {seed_id} not found or not in QUEUED state.")
            return False

        logger.info(f"Hunting for seed: {seed['title']}")
        
        # 1. Brave Search
        query = seed['title']
        if isinstance(seed['payload'], str):
            payload = json.loads(seed['payload'])
        else:
            payload = seed['payload']
            
        results = await self.search_client.search(query, count=3)
        
        if not results:
            logger.warning(f"No search results for seed: {seed_id}")
            return False

        # 2. Pick the best result (top 1 for now to save quota)
        target = results[0]
        logger.info(f"Targeting authoritative source: {target['url']}")

        # 3. Scrape & Distill via WebScout
        # Use simple distillation settings
        distiller = {
            "model": "distill-sieve", # Internal routing handled by llm_client in web_scout
            "base_url": "internal"
        }
        
        # Sprint 11: Recursive Depth for URGENT targets (Gravity >= 10.0)
        gravity = seed.get("gravity", 0.0)
        depth = 1 if gravity >= 10.0 else 0
        
        if depth > 0:
            logger.warning(f"⚡ HUNT: Processing URGENT target '{seed['title']}' with Depth {depth}")

        raw_data = await self.scout.discover({"url": target['url'], "depth": depth})
        findings = await self.scout.extract(raw_data, distiller, keywords=payload.get("keywords", []))

        # 4. Mark Seed as Completed (or update status)
        self.queue.complete_grain(seed_id)
        
        # 5. In a real scenario, we'd submit this to the mesh. 
        # For now, we've updated the MasterQueue and the brief engine will pick it up.
        logger.info(f"Successfully distilled finding for {seed_id}")
        return True

    async def autonomous_hunt(self):
        """Processes the highest gravity seed in the queue."""
        seeds = self.queue.list_open_inquiries()
        queued = [s for s in seeds if s['status'] == 'QUEUED']
        
        if not queued:
            logger.info("No queued seeds found. Nexus is idling.")
            return False
            
        top_seed = queued[0] # Highest gravity due to list_open_inquiries ordering
        return await self.process_seed(top_seed['id'])
