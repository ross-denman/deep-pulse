#!/usr/bin/env python3
"""
Deep Ledger — Neo4j Knowledge Graph Driver (Dual-Mode)

Async Neo4j driver that auto-selects between Local Docker and Aura Production
based on the NEO4J_URI in .env.

    Local:  bolt://localhost:7687  (Docker Compose)
    Aura:   neo4j+s://xxxx.databases.neo4j.io  (Production)

If no NEO4J_URI is set, defaults to bolt://localhost:7687.

Usage:
    async with GraphDriver() as driver:
        await driver.merge_entity(entity)
        await driver.merge_relationship(edge)
"""

import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.core.models import ExtractedEntity, RelationshipEdge, ScoutResult

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# ─── Configuration ──────────────────────────────────────────────

DEFAULT_URI = "bolt://localhost:7687"
DEFAULT_USER = "neo4j"
DEFAULT_PASSWORD = "deep-ledger-secret"


class GraphDriver:
    """Async Neo4j driver with dual-mode support (Local / Aura).

    Auto-detects Aura vs. Local based on the URI scheme.
    Uses MERGE for all write operations (idempotent, safe for re-runs).

    Args:
        uri: Override the NEO4J_URI from .env.
        user: Override the NEO4J_USER from .env.
        password: Override the NEO4J_PASSWORD from .env.
    """

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        self.uri = uri or os.getenv("NEO4J_URI", DEFAULT_URI)
        self.user = user or os.getenv("NEO4J_USER", DEFAULT_USER)
        self.password = password or os.getenv("NEO4J_PASSWORD", DEFAULT_PASSWORD)
        self._driver = None
        self._mode = "aura" if self.uri.startswith("neo4j+s://") else "local"

    async def __aenter__(self) -> "GraphDriver":
        """Open the Neo4j async driver connection."""
        try:
            from neo4j import AsyncGraphDatabase

            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
            logger.info(
                "Neo4j connected [%s]: %s",
                self._mode.upper(),
                self.uri,
            )
        except Exception as e:
            logger.error("Failed to connect to Neo4j (%s): %s", self.uri, e)
            self._driver = None
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close the Neo4j driver connection."""
        if self._driver:
            await self._driver.close()
            logger.info("Neo4j connection closed.")

    @property
    def is_connected(self) -> bool:
        """Check if the driver is connected."""
        return self._driver is not None

    @property
    def mode(self) -> str:
        """Return the current mode ('local' or 'aura')."""
        return self._mode

    # ─── Health Check ────────────────────────────────────────

    async def health_check(self) -> bool:
        """Verify Neo4j connectivity.

        Returns:
            True if Neo4j responds, False otherwise.
        """
        if not self._driver:
            return False
        try:
            async with self._driver.session() as session:
                result = await session.run("RETURN 1 AS ok")
                record = await result.single()
                return record is not None and record["ok"] == 1
        except Exception as e:
            logger.warning("Neo4j health check failed: %s", e)
            return False

    # ─── Entity Count ────────────────────────────────────────

    async def get_entity_count(self) -> int:
        """Return the total number of Entity nodes in the graph.

        Returns:
            Integer count of :Entity nodes.
        """
        if not self._driver:
            return 0
        try:
            async with self._driver.session() as session:
                result = await session.run(
                    "MATCH (e:Entity) RETURN count(e) AS cnt"
                )
                record = await result.single()
                return record["cnt"] if record else 0
        except Exception as e:
            logger.warning("Failed to count entities: %s", e)
            return 0

    async def get_entry_count(self) -> int:
        """Return the total number of IntelligenceEntry nodes.

        Returns:
            Integer count of :IntelligenceEntry nodes.
        """
        if not self._driver:
            return 0
        try:
            async with self._driver.session() as session:
                result = await session.run(
                    "MATCH (ie:IntelligenceEntry) RETURN count(ie) AS cnt"
                )
                record = await result.single()
                return record["cnt"] if record else 0
        except Exception as e:
            logger.warning("Failed to count entries: %s", e)
            return 0

    # ─── MERGE Operations ────────────────────────────────────

    async def merge_entity(self, entity: ExtractedEntity) -> bool:
        """MERGE an entity into the Knowledge Graph.

        Uses MERGE to be idempotent — safe for repeated scout runs.

        Args:
            entity: A validated ExtractedEntity.

        Returns:
            True if the MERGE succeeded.
        """
        if not self._driver:
            logger.warning("Neo4j not connected. Skipping entity merge: %s", entity.name)
            return False

        try:
            async with self._driver.session() as session:
                await session.run(
                    """
                    MERGE (e:Entity {name: $name})
                    SET e.entity_type = $entity_type,
                        e.description = $description,
                        e.confidence = $confidence,
                        e.last_updated = datetime()
                    """,
                    name=entity.name,
                    entity_type=entity.entity_type,
                    description=entity.description,
                    confidence=entity.confidence,
                )
            logger.info("Entity merged: %s (%s)", entity.name, entity.entity_type)
            return True
        except Exception as e:
            logger.error("Failed to merge entity %s: %s", entity.name, e)
            return False

    async def merge_intelligence_entry(
        self,
        scout_result: ScoutResult,
        cid: str,
        signature: str = "",
    ) -> bool:
        """MERGE an IntelligenceEntry into the Knowledge Graph.

        Args:
            scout_result: The validated ScoutResult.
            cid: The Content Identifier from the Ledger.
            signature: The Ed25519 signature hex.

        Returns:
            True if the MERGE succeeded.
        """
        if not self._driver:
            logger.warning("Neo4j not connected. Skipping entry merge: %s", cid)
            return False

        intel = scout_result.intel
        try:
            async with self._driver.session() as session:
                await session.run(
                    """
                    MERGE (ie:IntelligenceEntry {cid: $cid})
                    SET ie.type = $type,
                        ie.title = $title,
                        ie.status = 'speculative',
                        ie.perimeter = $perimeter,
                        ie.source_url = $source_url,
                        ie.scout_id = $scout_id,
                        ie.timestamp = datetime($timestamp),
                        ie.signature = $signature
                    """,
                    cid=cid,
                    type=intel.type,
                    title=intel.title,
                    perimeter=intel.perimeter,
                    source_url=scout_result.source_url,
                    scout_id=scout_result.scout_id,
                    timestamp=scout_result.timestamp.isoformat(),
                    signature=signature,
                )
            logger.info("IntelligenceEntry merged: %s", cid[:40])
            return True
        except Exception as e:
            logger.error("Failed to merge intelligence entry: %s", e)
            return False

    async def merge_relationship(self, edge: RelationshipEdge) -> bool:
        """MERGE a relationship between two entities in the Knowledge Graph.

        Note: Both entities must already exist. If either is missing,
        the relationship is silently skipped (MATCH will return no rows).

        Args:
            edge: A validated RelationshipEdge.

        Returns:
            True if the MERGE succeeded (or was a no-op due to missing entities).
        """
        if not self._driver:
            logger.warning(
                "Neo4j not connected. Skipping relationship: %s -[%s]-> %s",
                edge.source, edge.relationship_type, edge.target,
            )
            return False

        # Neo4j doesn't support parameterized relationship types,
        # so we use APOC or a safe switch. Since the type is a Literal
        # from Pydantic validation, it's safe to interpolate.
        cypher = f"""
            MATCH (a:Entity {{name: $source}})
            MATCH (b:Entity {{name: $target}})
            MERGE (a)-[r:{edge.relationship_type}]->(b)
            SET r.context = $context,
                r.confidence = $confidence,
                r.last_updated = datetime()
        """

        try:
            async with self._driver.session() as session:
                await session.run(
                    cypher,
                    source=edge.source,
                    target=edge.target,
                    context=edge.context,
                    confidence=edge.confidence,
                )
            logger.info(
                "Relationship merged: (%s)-[:%s]->(%s)",
                edge.source, edge.relationship_type, edge.target,
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to merge relationship %s -[%s]-> %s: %s",
                edge.source, edge.relationship_type, edge.target, e,
            )
            return False

    async def link_entry_to_entities(
        self, cid: str, entities: list[ExtractedEntity]
    ) -> int:
        """Create MENTIONS relationships from an IntelligenceEntry to its entities.

        Args:
            cid: The CID of the IntelligenceEntry.
            entities: List of entities mentioned in the entry.

        Returns:
            Number of MENTIONS relationships created.
        """
        if not self._driver:
            return 0

        linked = 0
        try:
            async with self._driver.session() as session:
                for entity in entities:
                    result = await session.run(
                        """
                        MATCH (ie:IntelligenceEntry {cid: $cid})
                        MATCH (e:Entity {name: $name})
                        MERGE (ie)-[r:MENTIONS]->(e)
                        SET r.last_updated = datetime()
                        RETURN count(r) AS cnt
                        """,
                        cid=cid,
                        name=entity.name,
                    )
                    record = await result.single()
                    if record and record["cnt"] > 0:
                        linked += 1
        except Exception as e:
            logger.error("Failed to link entry %s to entities: %s", cid[:20], e)

        logger.info("Linked entry %s to %d entities", cid[:20], linked)
        return linked

    # ─── Bulk Ingest from ScoutResult ────────────────────────

    async def ingest_scout_result(
        self,
        scout_result: ScoutResult,
        cid: str,
        signature: str = "",
    ) -> dict[str, Any]:
        """Full pipeline: ingest a ScoutResult into the Knowledge Graph.

        Merges all entities, the intelligence entry, all relationships,
        and links the entry to its entities via MENTIONS edges.

        Args:
            scout_result: A validated ScoutResult.
            cid: The Ledger CID for this entry.
            signature: The Ed25519 signature.

        Returns:
            Dict with counts: entities_merged, relationships_merged, entry_linked.
        """
        stats: dict[str, Any] = {
            "entities_merged": 0,
            "relationships_merged": 0,
            "entry_merged": False,
            "mentions_linked": 0,
        }

        if not self.is_connected:
            logger.warning("Neo4j not connected. Skipping full ingest.")
            return stats

        # 1. Merge all entities
        for entity in scout_result.entities:
            if await self.merge_entity(entity):
                stats["entities_merged"] += 1

        # 2. Merge the intelligence entry
        stats["entry_merged"] = await self.merge_intelligence_entry(
            scout_result, cid, signature
        )

        # 3. Merge all relationships
        for edge in scout_result.relationships:
            if await self.merge_relationship(edge):
                stats["relationships_merged"] += 1

        # 4. Link entry to its entities
        stats["mentions_linked"] = await self.link_entry_to_entities(
            cid, scout_result.entities
        )

        logger.info(
            "Ingest complete: %d entities, %d relationships, %d mentions",
            stats["entities_merged"],
            stats["relationships_merged"],
            stats["mentions_linked"],
        )
        return stats
