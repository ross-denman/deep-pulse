import os
import httpx
import logging
from typing import List, Dict, Any

logger = logging.getLogger("brave_search")

class BraveSearchClient:
    """
    Minimalist Brave Search API Client.
    Handles quota management and authoritative link extraction.
    """
    def __init__(self):
        self.api_key = os.getenv("BRAVE_API_KEY")
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        self._last_usage = {"limit": 1, "remaining": 1, "reset": 0}
        
        if not self.api_key:
            logger.warning("BRAVE_API_KEY not found in environment.")

    def get_usage_percent(self) -> float:
        """Returns the percentage of the quota used."""
        used = self._last_usage["limit"] - self._last_usage["remaining"]
        return (used / self._last_usage["limit"]) * 100

    async def search(self, query: str, count: int = 5) -> List[Dict[str, Any]]:
        """
        Executes a search and returns authoritative results.
        """
        if not self.api_key:
            return []

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key
        }
        params = {
            "q": query,
            "count": count,
            "text_decorations": False
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, headers=headers, params=params)
                
                # Update Quota Tracking
                self._last_usage["limit"] = int(response.headers.get("X-RateLimit-Limit", 1))
                self._last_usage["remaining"] = int(response.headers.get("X-RateLimit-Remaining", 1))
                self._last_usage["reset"] = int(response.headers.get("X-RateLimit-Reset", 0))
                
                response.raise_for_status()
                data = response.json()
                
                results = []
                for result in data.get("web", {}).get("results", []):
                    results.append({
                        "title": result.get("title"),
                        "url": result.get("url"),
                        "description": result.get("description")
                    })
                
                logger.info(f"Brave Search: Found {len(results)} results for '{query}' (Usage: {self.get_usage_percent():.1f}%)")
                return results
        except Exception as e:
            logger.error(f"Brave Search Error: {e}")
            return []
