#!/usr/bin/env python3
"""
Deep Ledger — LEAP Scout Agent

Specialized crawler for the LEAP District (Meta Infrastructure) perimeter.
Targets:
    1. IURC Electronic Filing System (EFS) — Data center related dockets
    2. Boone County — Water variance and zoning documents
    3. Indiana General Assembly — HB 1245 status and related bills

Uses Crawl4AI to convert government portals and PDFs into Markdown,
then extracts structured intelligence via the Intelligence Gate (Pydantic)
and the Internal Auditor (LLM NER), and MERGEs results into Neo4j.

Pipeline:
    Crawl → LEAPDistrictIntel (Pydantic) → Auditor NER → ScoutResult
    → create_entry() (signed) → Neo4j MERGE
"""

import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from src.agents.auditor import InternalAuditor
from src.core.identity import NodeIdentity
from src.core.ledger import create_entry
from src.core.models import (
    LEAPDistrictIntel,
    LedgerEntryPayload,
    ScoutResult,
)
from src.db.driver import GraphDriver

logger = logging.getLogger(__name__)

# ─── Target URLs ────────────────────────────────────────────────
TARGETS = {
    "iurc_search": {
        "url": "https://iurc.portal.in.gov/legal-and-policy/",
        "description": "IURC Legal & Policy Portal — docket filings",
        "keywords": ["data center", "meta", "rate impact", "HB 1245", "gigawatt"],
    },
    "iurc_annual_reports": {
        "url": "https://www.in.gov/iurc/about-the-commission/annual-reports/",
        "description": "IURC Annual Reports",
        "keywords": ["data center", "capacity", "electricity", "demand"],
    },
    "boone_county_gis": {
        "url": "https://www.boonecounty.in.gov/",
        "description": "Boone County Government Portal",
        "keywords": [
            "water variance",
            "zoning",
            "meta",
            "data center",
            "permit",
            "lebanon",
        ],
    },
    "indiana_hb1245": {
        "url": "https://iga.in.gov/",
        "description": "Indiana General Assembly — Bill Tracker",
        "keywords": ["HB 1245", "data center", "rate impact", "IURC study"],
    },
}


class LeapScout:
    """LEAP District Scout — Meta Infrastructure Intelligence Gatherer.

    This scout crawls government portals in Indiana to monitor Meta's
    $10B data center expansion and its impact on local infrastructure.

    Returns validated ScoutResult objects through the Intelligence Gate.
    Extracted entities and relationships are MERGEd into Neo4j.

    Args:
        identity: The signing node's identity.
        run_auditor: Whether to run the LLM NER pass. Default True.
        ingest_neo4j: Whether to MERGE results into Neo4j. Default True.
    """

    def __init__(
        self,
        identity: NodeIdentity,
        run_auditor: bool = True,
        ingest_neo4j: bool = True,
    ) -> None:
        self.identity = identity
        self.scout_id = "leap-scout-v1"
        self.run_auditor = run_auditor
        self.ingest_neo4j = ingest_neo4j
        self.results: list[dict[str, Any]] = []
        self.scout_results: list[ScoutResult] = []
        self._auditor = InternalAuditor() if run_auditor else None

    async def execute(self) -> list[dict[str, Any]]:
        """Execute the full LEAP scout mission.

        Crawls all target URLs, extracts structured intelligence through
        the Intelligence Gate, runs the Internal Auditor NER pass, signs
        Ledger entries, and MERGEs everything into Neo4j.

        Returns:
            List of signed JSON-LD Ledger entries.
        """
        logger.info("LEAP Scout deploying — targeting %d URLs", len(TARGETS))

        try:
            from crawl4ai import AsyncWebCrawler
        except ImportError:
            logger.warning(
                "crawl4ai not installed. Using fallback HTTP scraping."
            )
            return await self._fallback_scrape()

        entries = []

        async with AsyncWebCrawler(verbose=False) as crawler:
            for target_id, target in TARGETS.items():
                logger.info("Crawling: %s (%s)", target_id, target["url"])
                try:
                    result = await crawler.arun(url=target["url"])

                    if result.success and result.markdown:
                        entry = await self._process_target(
                            target_id=target_id,
                            markdown=result.markdown,
                            target=target,
                        )
                        if entry:
                            entries.append(entry)
                    else:
                        logger.warning(
                            "No content returned from %s (success=%s)",
                            target_id,
                            result.success,
                        )

                except Exception as e:
                    logger.error("Failed to crawl %s: %s", target_id, e)

        self.results = entries
        return entries

    async def _fallback_scrape(self) -> list[dict[str, Any]]:
        """Fallback scraper using httpx when Crawl4AI is unavailable.

        Returns:
            List of signed Ledger entries from basic HTTP scraping.
        """
        entries = []

        try:
            import httpx
        except ImportError:
            logger.error(
                "Neither crawl4ai nor httpx is available. Cannot scrape."
            )
            return entries

        async with httpx.AsyncClient(
            follow_redirects=True, timeout=30.0
        ) as client:
            for target_id, target in TARGETS.items():
                try:
                    response = await client.get(target["url"])
                    if response.status_code == 200:
                        entry = await self._process_target(
                            target_id=target_id,
                            markdown=response.text,
                            target=target,
                        )
                        if entry:
                            entries.append(entry)
                except Exception as e:
                    logger.error("Fallback scrape failed for %s: %s", target_id, e)

        self.results = entries
        return entries

    async def _process_target(
        self,
        target_id: str,
        markdown: str,
        target: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Process a single target through the full pipeline.

        Flow: extract intel → Pydantic validation → Auditor NER
              → ScoutResult → create_entry() → Neo4j MERGE

        Args:
            target_id: The target identifier.
            markdown: The scraped content.
            target: The target configuration dict.

        Returns:
            A signed Ledger entry, or None if extraction failed.
        """
        # Step 1: Extract typed intelligence (Intelligence Gate)
        intel = self._extract_intelligence(
            target_id=target_id,
            markdown=markdown,
            target=target,
        )
        if not intel:
            return None

        logger.info(
            "Intelligence extracted from %s: %s",
            target_id,
            intel.title,
        )

        # Step 2: Run Internal Auditor NER pass
        entities = []
        relationships = []
        if self._auditor:
            try:
                entities, relationships = await self._auditor.extract(
                    markdown=markdown,
                    keywords_matched=intel.keywords_matched,
                    target_description=target["description"],
                )
                logger.info(
                    "Auditor extracted %d entities, %d relationships from %s",
                    len(entities),
                    len(relationships),
                    target_id,
                )
            except Exception as e:
                logger.warning(
                    "Auditor NER failed for %s, proceeding without entities: %s",
                    target_id,
                    e,
                )

        # Step 3: Build validated ScoutResult
        scout_result = ScoutResult(
            scout_id=self.scout_id,
            source_url=target["url"],
            intel=intel,
            entities=entities,
            relationships=relationships,
            raw_markdown_length=len(markdown),
        )
        self.scout_results.append(scout_result)

        # Step 4: Create signed Ledger entry
        entry = create_entry(
            identity=self.identity,
            data=intel.model_dump(),
            source_url=target["url"],
            scout_id=self.scout_id,
            status="speculative",
        )

        # Step 5: MERGE into Neo4j Knowledge Graph
        if self.ingest_neo4j:
            try:
                async with GraphDriver() as driver:
                    if driver.is_connected:
                        stats = await driver.ingest_scout_result(
                            scout_result=scout_result,
                            cid=entry["id"],
                            signature=entry["proof"]["signature"],
                        )
                        logger.info(
                            "Neo4j ingest for %s: %s",
                            target_id,
                            stats,
                        )
                    else:
                        logger.warning(
                            "Neo4j not available. Skipping graph ingest for %s.",
                            target_id,
                        )
            except Exception as e:
                logger.warning(
                    "Neo4j ingest failed for %s (non-fatal): %s",
                    target_id,
                    e,
                )

        return entry

    def _extract_intelligence(
        self,
        target_id: str,
        markdown: str,
        target: dict[str, Any],
    ) -> LEAPDistrictIntel | None:
        """Extract structured intelligence from scraped content.

        Searches the markdown content for keyword matches and extracts
        relevant context windows around each match. Returns a validated
        Pydantic model instead of a raw dict.

        Args:
            target_id: The target identifier.
            markdown: The scraped content (as markdown or raw text).
            target: The target configuration dict.

        Returns:
            A validated LEAPDistrictIntel, or None if no keywords matched.
        """
        keywords = target["keywords"]
        content_lower = markdown.lower()

        # Find keyword matches
        matches = []
        for keyword in keywords:
            if keyword.lower() in content_lower:
                matches.append(keyword)

        if not matches:
            return None

        # Extract context windows (200 chars around each keyword match)
        snippets = []
        for keyword in matches:
            idx = content_lower.find(keyword.lower())
            if idx >= 0:
                start = max(0, idx - 200)
                end = min(len(markdown), idx + len(keyword) + 200)
                snippet = markdown[start:end].strip()
                snippet = re.sub(r"\s+", " ", snippet)
                snippets.append(snippet)

        # Deduplicate snippets
        unique_snippets = list(dict.fromkeys(snippets))[:5]

        # Build and validate through the Intelligence Gate
        intel = LEAPDistrictIntel(
            title=f"LEAP Scout — {target['description']}",
            target_id=target_id,
            keywords_matched=matches,
            keyword_hit_count=len(matches),
            total_keywords=len(keywords),
            content_length=len(markdown),
            snippets=unique_snippets,
            assessment=(
                f"Matched {len(matches)}/{len(keywords)} keywords. "
                f"Content contains references to: {', '.join(matches)}."
            ),
        )

        return intel


async def main() -> None:
    """Standalone scout execution for testing."""
    from src.core.identity import load_identity

    logging.basicConfig(level=logging.INFO)

    identity = load_identity()
    scout = LeapScout(identity)
    results = await scout.execute()

    print(f"\n  Scout returned {len(results)} entries:")
    for entry in results:
        print(f"    📎 {entry['id']}")
        print(f"       {entry['data'].get('title', 'N/A')}")
        print(f"       Keywords: {entry['data'].get('keywords_matched', [])}")
        print()

    if scout.scout_results:
        print(f"\n  Validated ScoutResults: {len(scout.scout_results)}")
        for sr in scout.scout_results:
            print(f"    🔬 {sr.intel.title}")
            print(f"       Entities: {len(sr.entities)}")
            print(f"       Relationships: {len(sr.relationships)}")
            for entity in sr.entities:
                print(f"         → {entity.name} ({entity.entity_type}) [{entity.confidence:.0%}]")
            print()


if __name__ == "__main__":
    asyncio.run(main())
