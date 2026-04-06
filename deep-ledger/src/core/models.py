#!/usr/bin/env python3
"""
Deep Ledger — Intelligence Gate (Pydantic Schemas)

All Scout outputs MUST validate against these models before touching
the Ledger or the Knowledge Graph. This is the "Forced Verification"
layer — if a Scout returns data that doesn't match the schema, the
Deep Ledger rejects it before it can ever be signed or gossiped.

Models:
    ExtractedEntity   — A named entity from scouted content.
    RelationshipEdge  — A suggested link between two entities.
    LEAPDistrictIntel — Typed payload for the LEAP perimeter.
    ScoutResult       — Top-level wrapper for all scout output.
    LedgerEntryPayload — Validated bundle for create_entry().
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ─── Entity Types (mirrors Neo4j :Entity.entity_type) ───────────

EntityType = Literal[
    "Corporation",
    "Agency",
    "Location",
    "Project",
    "Legislation",
    "Resource",
    "Person",
    "Organization",
]

# ─── Relationship Types (mirrors Neo4j edge labels) ─────────────

RelationshipType = Literal[
    "MENTIONS",
    "CONSUMES",
    "REGULATES",
    "LOCATED_IN",
    "LINKED_TO",
    "BUILDING",
    "OVERSEES",
    "MONITORS",
    "EXCEEDS",
    "SUPPLIES",
    "FUNDS",
    "OPPOSES",
    "SUPPORTS",
]


# ─── Extracted Entity ────────────────────────────────────────────

class ExtractedEntity(BaseModel):
    """A named entity extracted from scouted intelligence.

    Attributes:
        name: The canonical name of the entity (e.g., "Meta Platforms").
        entity_type: One of the defined EntityType literals.
        description: A brief description of the entity's relevance.
        confidence: Extraction confidence score (0.0–1.0).
    """

    name: str = Field(..., min_length=1, max_length=256)
    entity_type: EntityType
    description: str = Field(default="", max_length=1024)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        """Strip whitespace and normalize entity names."""
        return v.strip()


# ─── Relationship Edge ──────────────────────────────────────────

class RelationshipEdge(BaseModel):
    """A suggested relationship between two entities.

    Enables the NER pass to propose typed links like:
        (Meta Platforms)-[:CONSUMES]->(Water Supply)
        (HB 1245)-[:REGULATES]->(Meta Platforms)

    Attributes:
        source: Name of the source entity.
        target: Name of the target entity.
        relationship_type: The Neo4j relationship label.
        context: Brief explanation of why this relationship was inferred.
        confidence: Extraction confidence score (0.0–1.0).
    """

    source: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)
    relationship_type: RelationshipType
    context: str = Field(default="", max_length=512)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


# ─── LEAP District Intel ────────────────────────────────────────

class LEAPDistrictIntel(BaseModel):
    """Typed intelligence payload for the LEAP District perimeter.

    Replaces the raw dict previously returned by LeapScout._extract_intelligence().

    Attributes:
        type: Always "LEAPDistrictIntel" — used for discriminated unions.
        title: Human-readable title of the intelligence.
        target_id: The Scout target identifier (e.g., "iurc_search").
        keywords_matched: List of keywords that matched in the content.
        keyword_hit_count: Number of keywords matched.
        total_keywords: Total keywords searched.
        content_length: Length of the source markdown in characters.
        snippets: Context windows around keyword matches.
        perimeter: Intelligence perimeter name.
        region: Geographic region.
        assessment: Human-readable assessment of the findings.
    """

    type: Literal["LEAPDistrictIntel"] = "LEAPDistrictIntel"
    title: str
    target_id: str
    keywords_matched: list[str] = Field(default_factory=list)
    keyword_hit_count: int = Field(ge=0)
    total_keywords: int = Field(ge=0)
    content_length: int = Field(ge=0)
    snippets: list[str] = Field(default_factory=list, max_length=10)
    perimeter: str = "Meta Infrastructure — LEAP District"
    region: str = "Lebanon, Indiana (Boone County)"
    assessment: str = ""


# ─── Scout Result ────────────────────────────────────────────────

class ScoutResult(BaseModel):
    """Top-level wrapper for all Scout output.

    Every scout execution produces a ScoutResult containing the typed
    intelligence payload, extracted entities, and suggested relationships.

    Attributes:
        scout_id: Identifier for the scout (e.g., "leap-scout-v1").
        source_url: The URL that was scouted.
        timestamp: When the scout executed (UTC).
        intel: The typed intelligence payload.
        entities: Named entities extracted via the NER agentic pass.
        relationships: Suggested relationship edges between entities.
        raw_markdown_length: Length of the source content (for audit trail).
    """

    scout_id: str
    source_url: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    intel: LEAPDistrictIntel  # Future: discriminated union for multiple perimeters
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relationships: list[RelationshipEdge] = Field(default_factory=list)
    raw_markdown_length: int = Field(default=0, ge=0)


# ─── Ledger Entry Payload ────────────────────────────────────────

class LedgerEntryPayload(BaseModel):
    """Validated data bundle for create_entry().

    This is the final gate before an intelligence entry gets signed
    and appended to the JSON-LD Ledger.

    Attributes:
        data: The typed intelligence payload (serialized to dict).
        source_url: Origin URL.
        scout_id: Scout that discovered the data.
        status: Entry verification status.
        entities: Entities to MERGE into Neo4j.
        relationships: Relationship edges to MERGE into Neo4j.
    """

    data: dict  # from intel.model_dump()
    source_url: str
    scout_id: str = "genesis"
    status: Literal["speculative", "pending_verification", "verified"] = (
        "speculative"
    )
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relationships: list[RelationshipEdge] = Field(default_factory=list)
