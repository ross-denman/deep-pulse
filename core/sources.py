#!/usr/bin/env python3
"""
Deep Ledger — Source Validator (The Epistemic Firewall)

Implements logic to classify and weight data sources based on the 
genesis_sources.jsonld whitelist.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Paths
CORE_DIR = Path(__file__).resolve().parent
GENESIS_SOURCES_FILE = CORE_DIR / "genesis_sources.jsonld"

class SourceValidator:
    """Validates and weights data sources for the Epistemic Firewall."""

    def __init__(self):
        self.sources = self._load_genesis_sources()

    def _load_genesis_sources(self) -> List[Dict[str, Any]]:
        """Load the authoritative source whitelist."""
        if not GENESIS_SOURCES_FILE.exists():
            logger.warning(f"Genesis sources file not found at {GENESIS_SOURCES_FILE}. Using defaults.")
            return []
        
        try:
            with open(GENESIS_SOURCES_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load genesis sources: {e}")
            return []

    def get_source_metadata(self, url: str) -> Dict[str, Any]:
        """
        Determines the weight and status of a data source URL.
        
        Returns:
            Dict containing weight, is_institutional, is_notary_vetted, and is_volatile.
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Default metadata for unknown sources
        metadata = {
            "domain": domain,
            "weight": 0.4, # Tertiary default
            "is_institutional": False,
            "is_notary_vetted": False,
            "is_volatile": False,
            "tier": "Tertiary"
        }

        # Check for domain matches
        for src in self.sources:
            src_domain = src["domain"].lower()
            # Match either exact domain or if the URL ends with .domain (e.g. .gov)
            if domain == src_domain or domain.endswith(f".{src_domain}"):
                metadata.update({
                    "weight": src.get("weight", 0.4),
                    "is_institutional": src.get("is_institutional", False),
                    "is_notary_vetted": src.get("is_notary_vetted", False),
                    "is_volatile": src.get("is_volatile", False),
                    "tier": src.get("tier", "Tertiary")
                })
                break
        
        return metadata

    def is_volatile(self, url: str) -> bool:
        """Check if a source is flagged as a social/ephemeral volatility spike."""
        return self.get_source_metadata(url).get("is_volatile", False)

    def get_multiplier(self, url: str) -> float:
        """Calculate the multiplier for the source (Institutional Anchor bonus)."""
        meta = self.get_source_metadata(url)
        if meta.get("is_institutional"):
            return 1.5 # Sovereign Multiplier
        return 1.0

# Global Instance
source_validator = SourceValidator()
