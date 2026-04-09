import asyncio
import logging
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from typing import List, Dict, Any

from src.private.master_queue import MasterOutpostQueue

logger = logging.getLogger("onion_gateway")

class OnionRSSGateway:
    """
    Onion RSS Gateway (Anonymous Ingestion).
    Polls .onion RSS feeds via Tor proxy and enqueues findings as Truth Seeds.
    """
    def __init__(self, tor_proxy: str = "socks5://127.0.0.1:9050", interval_minutes: int = 60):
        self.tor_proxy = tor_proxy
        self.interval = interval_minutes * 60
        self.queue = MasterOutpostQueue()
        self.running = True
        
        # List of .onion RSS feeds to monitor
        # In a real scenario, these would be loaded from a gitignored config
        self.feeds = [
            "http://rss-sifter-demo.onion/feed.xml", # Example Demo Feed
        ]

    async def poll_feeds(self):
        """Main loop for polling RSS feeds."""
        logger.info(f"🧅 Onion RSS Gateway active. Polling {len(self.feeds)} feeds via Tor...")
        
        while self.running:
            for feed_url in self.feeds:
                try:
                    await self.process_feed(feed_url)
                except Exception as e:
                    logger.error(f"Failed to poll feed {feed_url}: {e}")
            
            logger.info(f"Sleeping for {self.interval // 60}m before next Onion sweep.")
            await asyncio.sleep(self.interval)

    async def process_feed(self, url: str):
        """Fetch and parse a single RSS feed."""
        async with httpx.AsyncClient(proxies=self.tor_proxy, timeout=30.0) as client:
            # Mocking response for demo if .onion is unreachable
            if ".onion" in url:
                logger.info(f"Routing request for {url} through Tor...")
            
            try:
                response = await client.get(url)
                response.raise_for_status()
                xml_data = response.text
                await self._parse_and_enqueue(xml_data, url)
            except Exception as e:
                # For Phase 2, we log the failure but don't crash
                logger.warning(f"Could not reach {url}. Ensure Tor local bridge is active. Error: {e}")

    async def _parse_and_enqueue(self, xml_data: str, source_url: str):
        """Parse RSS XML and inject into MasterQueue."""
        root = ET.fromstring(xml_data)
        items = root.findall(".//item")
        
        count = 0
        for item in items:
            title = item.find("title").text if item.find("title") is not None else "Untitled Pulse"
            link = item.find("link").text if item.find("link") is not None else source_url
            description = item.find("description").text if item.find("description") is not None else ""
            
            # Generate a stable Grain ID from the link
            grain_id = hashlib.sha256(link.encode()).hexdigest()[:12]
            
            payload = {
                "origin": "RSS_SIFTER",
                "link": link,
                "description": description,
                "discovery_type": "ANONYMOUS_PULSE"
            }
            
            # Enqueue as a Truth Seed with moderate gravity
            success = self.queue.enqueue_grain(
                grain_id=f"onion_{grain_id}",
                title=title,
                payload=payload,
                source_chaff=link,
                gravity=7.0, # Higher gravity for deep-web signals
                probe_id="RSS_SIFTER_V1"
            )
            if success:
                count += 1
        
        if count > 0:
            logger.info(f"Ingested {count} anonymous Pulses from {source_url}")

    def stop(self):
        self.running = False

async def main():
    # Simple runner for the gateway
    tor_proxy = os.getenv("TOR_PROXY", "socks5://127.0.0.1:9050")
    gateway = OnionRSSGateway(tor_proxy=tor_proxy)
    await gateway.poll_feeds()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
