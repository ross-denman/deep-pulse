import json
import logging
from pathlib import Path
from typing import Any, Dict, List
try:
    from base_probe import BaseCuriosityProbe
except ImportError:
    from ..base_probe import BaseCuriosityProbe

logger = logging.getLogger("source_auditor")

class SourceAuditor(BaseCuriosityProbe):
    """
    The SourceAuditor Module.
    Tracks $SR-G (Source Reputation) and promotes sources through the 
    Speculative -> Probationary -> Verified lifecycle.
    """
    name = "Source Auditor"
    category = "logic"
    description = "Tracks Signal-to-Noise, Accuracy, and Latency for data sources."
    
    # Triggered by 'audit' seeds or when a grain needs verification
    input_types = ["source_audit", "grain_validation"]
    output_types = ["reputation_update"]

    def __init__(self, outpost_id: str, bridge_url: str = "http://localhost:4110"):
        super().__init__(outpost_id, bridge_url)
        # Reputation database location (Sprint 06 Standard)
        self.repo_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "harvest" / "source_reputation.json"
        self._ensure_repo()

    def _ensure_repo(self):
        """Ensures the reputation database exists."""
        if not self.repo_path.parent.exists():
            self.repo_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.repo_path.exists():
            with open(self.repo_path, "w") as f:
                json.dump({}, f)

    def _load_reputation(self) -> Dict[str, Dict]:
        with open(self.repo_path, "r") as f:
            return json.load(f)

    def _save_reputation(self, data: Dict[str, Dict]):
        with open(self.repo_path, "w") as f:
            json.dump(data, f, indent=4)

    def harvest(self, seed: Dict[str, Any] = None) -> List[Any]:
        """
        In logic tier, harvest often receives a 'grain' or 'source' to audit.
        If seed is None, it audits the entire local library.
        """
        if seed:
            return [seed]
        
        # Periodic audit: return all speculative/probationary sources
        repo = self._load_reputation()
        return [{"type": "source_audit", "source": url, "data": meta} for url, meta in repo.items()]

    def sift(self, raw_entries: List[Any]) -> List[Dict[str, Any]]:
        """
        Calculates Signal-to-Noise and Latency. 
        Promotes sources based on successful corroboration yield.
        """
        grains = []
        repo = self._load_reputation()

        for entry in raw_entries:
            source_url = entry.get("source")
            if not source_url: continue

            meta = repo.get(source_url, {
                "sr_g": 0,
                "status": "SPECULATIVE",
                "total_grains": 0,
                "settled_grains": 0,
                "signal_to_noise": 0.0,
                "accuracy": 0.0,
                "latency": 0.0
            })

            # Logic: Update SR-G based on performance
            # promotion threshold: 10 settled grains
            if meta["settled_grains"] >= 10 and meta["status"] == "PROBATIONARY":
                meta["status"] = "VERIFIED"
                logger.info(f"[WIN] [SOURCE PROMOTED] {source_url} is now VERIFIED.")

            # Calculate Signal-to-Noise
            if meta["total_grains"] > 0:
                meta["signal_to_noise"] = meta["settled_grains"] / meta["total_grains"]

            repo[source_url] = meta
            grain = {
                "id": f"audit_{hash(source_url)}",
                "type": "reputation_update",
                "source": source_url,
                "meta": meta
            }
            grains.append(self.seal_grain(grain))

        self._save_reputation(repo)
        return grains

    def settle(self, grain: Dict[str, Any]) -> bool:
        """Logic probes often settle by updating local state or bridge metadata."""
        logger.info(f"[VAL] [SR-G UPDATE] {grain['source']} -> {grain['meta']['sr_g']} ($SR-G)")
        return True
