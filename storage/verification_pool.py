import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from core.contracts import VerificationRequest

logger = logging.getLogger("verification_pool")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
POOL_FILE = PROJECT_ROOT / "the-chronicle" / "harvest" / "verification_pool.jsonld"

class VerificationPool:
    """
    The Public Verification Queue.
    Gossiped across the mesh to announce pending discoveries awaiting consensus.
    """
    def __init__(self, pool_file: Path = POOL_FILE):
        self.pool_file = pool_file
        self.pool_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_pool()

    def _load_pool(self) -> List[Dict[str, Any]]:
        if not self.pool_file.exists():
            return []
        try:
            with open(self.pool_file, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def save_pool(self, requests: List[Dict[str, Any]]):
        with open(self.pool_file, "w") as f:
            json.dump(requests, f, indent=2)

    def add_request(self, request: VerificationRequest):
        pool = self._load_pool()
        # Prevent duplicates
        if any(r["grain_id"] == request.grain_id for r in pool):
            return False
            
        pool.append(request.model_dump(mode="json"))
        self.save_pool(pool)
        logger.info(f"Added VerificationRequest: {request.grain_id} to the pool.")
        return True

    def get_open_requests(self) -> List[Dict[str, Any]]:
        pool = self._load_pool()
        return [r for r in pool if r["status"] == "OPEN"]

    def update_status(self, grain_id: str, status: str):
        pool = self._load_pool()
        for r in pool:
            if r["grain_id"] == grain_id:
                r["status"] = status
                break
        self.save_pool(pool)
