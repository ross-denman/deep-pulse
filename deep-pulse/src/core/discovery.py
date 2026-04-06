import os
import logging
import httpx
from typing import List

logger = logging.getLogger(__name__)

class BraveDiscovery:
    """Uses the Brave Search API as a Genesis Phase discovery layer."""
    
    def __init__(self):
        self.api_key = os.getenv("BRAVE_API_KEY")
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        if not self.api_key:
            logger.warning("BRAVE_API_KEY not set. Broad Scan phase will fail if no targets provided.")

    async def search(self, query: str, count: int = 5) -> List[str]:
        """Performs a web search to fetch target URLs for an empty perimeter."""
        if not self.api_key:
            return []

        logger.info(f"Initiating Brave Search Broad Scan for: '{query}'")
        
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key
        }
        
        params = {
            "q": query,
            "count": count
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(self.base_url, headers=headers, params=params, timeout=15.0)
                resp.raise_for_status()
                data = resp.json()
                
                urls = []
                results = data.get("web", {}).get("results", [])
                for result in results:
                    urls.append(result.get("url"))
                    if len(urls) >= count:
                        break
                        
                logger.info(f"Discovered {len(urls)} genesis points.")
                return urls
        except Exception as e:
            logger.error(f"Brave Search API failed: {e}")
            return []
