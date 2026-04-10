import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any

from src.public.core.chronicle import read_ledger
from src.public.core.models import InterestProfile, PeriodicalBrief, BriefEntry

# Setup logging
logger = logging.getLogger("briefing_engine")

class BriefingEngine:
    """
    Synthesizes the Chronicle into a machine-readable JSON digest.
    Filters findings based on the user's Interest Profile.
    """
    def __init__(self, 
                 profile_path: str = "harvest/user_profile.json",
                 ledger_path: str = "harvest/chronicle.jsonld"):
        self.profile_path = Path(profile_path)
        self.ledger_path = Path(ledger_path)

    def load_profile(self) -> InterestProfile:
        if not self.profile_path.exists():
            return InterestProfile()
        with open(self.profile_path, 'r') as f:
            return InterestProfile(**json.load(f))

    def synthesize_digest(self, hours_back: int = 24) -> PeriodicalBrief:
        """
        Scans the ledger for entries matching the profile within the time window.
        Returns a PeriodicalBrief object (JSON-ready).
        """
        profile = self.load_profile()
        ledger = read_ledger() # Returns list of dicts
        
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=hours_back)
        
        brief = PeriodicalBrief(
            start_time=start_time,
            end_time=now,
            findings=[],
            friction_report=[]
        )

        for entry in ledger:
            # 1. Temporal Filter & Schema Safety
            if 'metadata' not in entry or 'data' not in entry:
                continue

            try:
                ts = datetime.fromisoformat(entry['metadata']['timestamp'])
                if ts < start_time:
                    continue
            except (KeyError, ValueError):
                continue

            # 2. Interest Filter (Keywords, Perimeters, Entities)
            data = entry.get('data', {})
            content_str = json.dumps(data).lower()
            match = False
            
            # Match keywords
            for kw in profile.keywords:
                if kw.lower() in content_str:
                    match = True
                    break
            
            # Match entities
            if not match:
                for entity in profile.entities:
                    if entity.lower() in content_str:
                        match = True
                        break

            if match:
                finding = BriefEntry(
                    title=data.get('title', 'Untitled Discovery'),
                    summary=data.get('description', data.get('payload', 'No summary available.')),
                    confidence=entry.get('metadata', {}).get('confidence', 1.0),
                    source=entry.get('metadata', {}).get('source_url', 'Mesh Discovery'),
                    cid=entry['id']
                )
                brief.findings.append(finding)
            
            # 3. Friction Filter (ConflictEvents)
            if data.get('type') == 'ConflictEvent':
                brief.friction_report.append(
                    f"Conflict detected at {entry['metadata']['timestamp']}: {entry['id'][:12]} [Source Clash]"
                )

        logger.info(f"Synthesis Complete: {len(brief.findings)} findings extracted from the last {hours_back}h.")
        return brief

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = BriefingEngine()
    digest = engine.synthesize_digest(hours_back=168) # 1 week
    print(digest.model_dump_json(indent=4))
