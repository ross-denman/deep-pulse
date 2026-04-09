import feedparser
import json
import logging
import os
import hashlib
import sys
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

# Add library root to path for interface access
LIBRARY_ROOT = Path(__file__).resolve().parent.parent
if str(LIBRARY_ROOT) not in sys.path:
    sys.path.append(str(LIBRARY_ROOT))

# Project root for core access
PROJECT_ROOT = LIBRARY_ROOT.parent.parent.parent
if str(PROJECT_ROOT / "src" / "public") not in sys.path:
    sys.path.append(str(PROJECT_ROOT / "src" / "public"))

try:
    from base_probe import BaseCuriosityProbe
    from src.public.core.chronicle import create_entry
    from src.public.core.identity import load_identity
except ImportError:
    # Handle direct execution or different relative paths
    from ..base_probe import BaseCuriosityProbe
    from src.public.core.chronicle import create_entry
    from src.public.core.identity import load_identity

logger = logging.getLogger("rss_sifter")

class RSSSifter(BaseCuriosityProbe):
    """
    Sifts institutional RSS feeds for Grains of Truth. (Plugin Version)
    """
    def __init__(self, outpost_id: str, bridge_url: str = "http://localhost:4110"):
        super().__init__(outpost_id, bridge_url)
        self.name = "Institutional RSS Sifter"
        self.category = "surface"
        self.description = "Passive harvesting of government newsroom and real estate feeds."
        self.probe_id = "RSS_SIFTER_V2"
        
        # State tracking (local persistence)
        self.state_file = PROJECT_ROOT / "harvest" / "probe_state.json"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.settled_entries = self._load_state()
        self.identity = load_identity()

    def _load_state(self) -> set:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    return set(json.load(f))
            except Exception as e:
                logger.warning(f"Failed to load probe state: {e}")
                return set()
        return set()

    def _save_state(self):
        try:
            with open(self.state_file, "w") as f:
                json.dump(list(self.settled_entries), f)
        except Exception as e:
            logger.error(f"Failed to save probe state: {e}")

    def harvest(self) -> List[Any]:
        """Ingests raw entries from feeds defined in profile.json."""
        urls = self.profile.get("feeds", [])
        all_entries = []
        for url in urls:
            try:
                logger.info(f"Harvesting from {url}...")
                feed = feedparser.parse(url)
                if feed.bozo:
                    logger.warning(f"Feed error on {url}: {feed.bozo_exception}")
                all_entries.extend(feed.entries)
            except Exception as e:
                logger.error(f"Failed to harvest {url}: {e}")
        return all_entries

    def sift(self, raw_entries: List[Any]) -> List[Dict[str, Any]]:
        """Identify grains and check for persistence using profile keywords."""
        grains = []
        keywords = self.profile.get("keywords", [])
        
        for entry in raw_entries:
            link = getattr(entry, 'link', '')
            if not link:
                continue
            
            entry_id = hashlib.sha256(link.encode()).hexdigest()
            if entry_id in self.settled_entries:
                continue
            
            content = entry.get("summary", "") or entry.get("description", "") or ""
            title = entry.get("title", "")
            full_text = (title + " " + content).lower()

            if any(word.lower() in full_text for word in keywords):
                logger.info(f"✨ [GRAIN DETECTED] {title[:60]}...")
                grain = {
                    "id": entry_id,
                    "title": title,
                    "content": content,
                    "link": link,
                    "timestamp": entry.get("published", datetime.now().isoformat()) if 'published' in entry else ""
                }
                grains.append(grain)
        return grains

    def settle(self, grain: Dict[str, Any]) -> bool:
        """Notarize and create payload for bridge submission."""
        logger.info(f"Settling grain: {grain['title']}")
        
        # 1. Structure the data for the Chronicle
        data = {
            "type": "IntelligencePulse",
            "title": grain["title"],
            "summary": grain["content"][:300],
            "source": grain["link"],
            "discovery": {
                "id": grain["id"],
                "origin": self.probe_id,
                "original_timestamp": grain["timestamp"]
            }
        }
        
        # 2. Create the sealed entry
        try:
            entry = create_entry(
                identity=self.identity,
                data=data,
                source_url=grain["link"],
                probe_id=self.probe_id,
                status="speculative",
                rep_g=self.profile.get("gravity_default", 5)
            )
            
            # 3. Save as local pulse payload
            pulse_dir = PROJECT_ROOT / "harvest" / "pulses"
            pulse_dir.mkdir(parents=True, exist_ok=True)
            payload_path = pulse_dir / f"pulse_{grain['id'][:8]}.json"
            
            with open(payload_path, "w") as f:
                json.dump(entry, f, indent=2)
                
            logger.info(f"Generated sealed pulse: {payload_path}")
            
            # 4. Update state to prevent re-settlement
            self.settled_entries.add(grain["id"])
            self._save_state()
            return True
        except Exception as e:
            logger.error(f"Failed to settle grain {grain['id']}: {e}")
            return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    from src.public.core.identity import load_identity
    identity = load_identity()
    sifter = RSSSifter(outpost_id=identity.outpost_id)
    
    chaff = sifter.harvest()
    grains = sifter.sift(chaff)
    for grain in grains:
        sifter.settle(grain)
