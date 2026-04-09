import abc
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

from core.identity import load_identity

logger = logging.getLogger("base_probe")

class BaseCuriosityProbe(abc.ABC):
    """
    The DNA of the Discovery Mesh Curiosity Probes.
    Ensures every probe speaks the same forensic language.
    """

    def seal_grain(self, grain: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cryptographically seals a Grain of Truth with the Outpost's Ed25519 identity.
        This provides 'Signature Hardening' for multi-stage investigative chains.
        """
        try:
            identity = load_identity()
            # Canonical JSON for stable signing
            raw_data = json.dumps(grain, sort_keys=True).encode()
            signature = identity.sign(raw_data)
            
            grain["proof"] = {
                "seal": signature,
                "outpost_id": identity.outpost_id,
                "verificationMethod": identity.public_key_hex
            }
            return grain
        except Exception as e:
            logger.error(f"Failed to seal grain: {e}")
            return grain

    def __init__(self, outpost_id: str, bridge_url: str = "http://localhost:4110"):
        self.outpost_id = outpost_id
        self.bridge_url = bridge_url
        self.probe_id = self.__class__.__name__
        self.name = getattr(self, "name", self.probe_id)
        self.category = getattr(self, "category", "general")
        self.description = getattr(self, "description", "A standard curiosity probe.")
        # Sprint 06: Dynamic Entity-Type Matching
        self.input_types = getattr(self, "input_types", [])
        self.output_types = getattr(self, "output_types", [])
        self.profile = self._load_profile()

    def _load_profile(self) -> Dict[str, Any]:
        """Loads profile.json from the module's directory."""
        # Find the directory of the subclass
        module = sys.modules[self.__class__.__module__]
        if hasattr(module, "__file__"):
            module_dir = Path(module.__file__).parent
            profile_path = module_dir / "profile.json"
            if profile_path.exists():
                try:
                    with open(profile_path, "r") as f:
                        logger.info(f"Loading discovery profile for {self.probe_id}...")
                        return json.load(f)
                except Exception as e:
                    logger.error(f"Failed to load profile for {self.probe_id}: {e}")
        return {}

    @abc.abstractmethod
    def harvest(self, seed: Dict[str, Any] = None) -> List[Any]:
        """Ingests the 'Chaff' (raw data entries). Optional seed for recursive triggers."""
        raise NotImplementedError

    @abc.abstractmethod
    def sift(self, raw_entries: List[Any]) -> List[Dict[str, Any]]:
        """Identifies Grains of Truth (the value). Override this to filter and format grains."""
        raise NotImplementedError

    @abc.abstractmethod
    def settle(self, grain: Dict[str, Any]) -> bool:
        """Notarizes and sends the grain to the bridge server. Override this to handle submission."""
        raise NotImplementedError
