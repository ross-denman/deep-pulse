import json
import logging
import re
import httpx
from typing import Any, Dict, List
try:
    from base_probe import BaseCuriosityProbe
except ImportError:
    from ..base_probe import BaseCuriosityProbe

logger = logging.getLogger("library_builder")

class LibraryBuilder(BaseCuriosityProbe):
    """
    The LibraryBuilder Forensic Probe.
    Monitors 'Seed Repositories' (Awesome Lists, Reddit) for new URLs.
    Flags new sources as SPECULATIVE and triggers SourceAuditor.
    """
    name = "Library Builder"
    category = "forensic"
    description = "Harvests investigative seeds from Awesome Lists and Reddit."
    
    # Acts on 'url' entities found by other probes (or seeded initially)
    input_types = ["url", "github_repo"]
    output_types = ["source_audit"]

    def harvest(self, seed: Dict[str, Any] = None) -> List[Any]:
        """Pulls raw content from the seed URL."""
        url = seed.get("value") if seed else "https://github.com/vinta/awesome-python"
        
        # Filter for known 'Awesome' patterns or repository links
        if not url.startswith("http"):
            return []

        logger.info(f"⛏️  [HARVESTING SEEDS] {url}...")
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                # Add generic User-Agent for GitHub/Reddit
                headers = {"User-Agent": "Mozilla/5.0 (SovereignAuditor/1.0; CuriosityOutpost)"}
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    return [{"content": resp.text, "url": url}]
        except Exception as e:
            logger.error(f"LibraryBuilder failed to harvest {url}: {e}")
        
        return []

    def sift(self, raw_entries: List[Any]) -> List[Dict[str, Any]]:
        """Identifies new investigative URLs (seeds) within the content."""
        findings = []
        for entry in raw_entries:
            html = entry.get("content", "")
            base_url = entry.get("url", "")
            
            # Simple heuristic: find all absolute http links
            # In a real scenario, this would use BeautifulSoup or specialized logic for markdown
            links = re.findall(r'href="(https?://[a-zA-Z0-9\-\.\/]+)"', html)
            
            # Filter for unique links and exclude common junk
            unique_links = list(set(links))
            filtered_links = [l for l in unique_links if not any(x in l for x in ["github.com", "google.com", "twitter.com"])]

            for link in filtered_links[:15]: # Governor: Limit seeds per list
                finding = {
                    "id": f"seed_{abs(hash(link))}",
                    "title": f"New Investigative Seed: {link[:40]}",
                    "type": "source_audit",
                    "source": base_url,
                    "entities": [
                        {"type": "source_audit", "value": link},
                        {"type": "url", "value": link} # Feed back as URL for potential recursive deep-portals
                    ],
                    "metadata": {
                        "discovered_at": base_url,
                        "status": "SPECULATIVE"
                    }
                }
                findings.append(self.seal_grain(finding))
        
        return findings

    def settle(self, grain: Dict[str, Any]) -> bool:
        """LibraryBuilder settles by notifying the bridge of a new potential reference."""
        # The bridge.py already has update_source_reputation called via the runner
        # but we can also log the discovery here.
        url = grain["entities"][0]["value"]
        logger.info(f"🌱 [NEW SEED DISCOVERED] Found {url}")
        return True
