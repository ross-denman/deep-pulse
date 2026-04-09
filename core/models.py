#!/usr/bin/env python3
"""
The Chronicle - Intelligence Gate (Pydantic Schemas)

All Probe outputs MUST validate against these models before touching
the Public Chronicle or the Knowledge Graph. This is the "Forced Verification"
layer - if a Probe returns data that doesn't match the schema, the
Public Chronicle rejects it before it can ever be sealed or gossiped.

Models:
    ExtractedEntity   - A named entity from scouted content.
    RelationshipEdge  - A suggested link between two entities.
    LEAPDistrictIntel - Typed payload for the LEAP perimeter.
    ProbeResult       - Top-level wrapper for all probe output.
    ChronicleEntryPayload - Validated bundle for create_entry().
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal, Union, Dict, List, Any, Optional
from pydantic import BaseModel, Field, field_validator


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Entity Types (mirrors Neo4j :Entity.entity_type) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

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

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Relationship Types (mirrors Neo4j edge labels) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

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


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Extracted Entity Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

class ExtractedEntity(BaseModel):
    """A named entity extracted from scouted intelligence.

    Attributes:
        name: The canonical name of the entity (e.g., "Meta Platforms").
        entity_type: One of the defined EntityType literals.
        description: A brief description of the entity's relevance.
        confidence: Extraction confidence score (0.0Ã¢â‚¬â€œ1.0).
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


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Relationship Edge Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

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
        confidence: Extraction confidence score (0.0Ã¢â‚¬â€œ1.0).
    """

    source: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)
    relationship_type: RelationshipType
    context: str = Field(default="", max_length=512)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ LEAP District Intel Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

class LEAPDistrictIntel(BaseModel):
    """Typed intelligence payload for the LEAP District perimeter.

    Replaces the raw dict previously returned by LeapScout._extract_intelligence().

    Attributes:
        type: Always "LEAPDistrictIntel" - used for discriminated unions.
        title: Human-readable title of the intelligence.
        target_id: The Probe target identifier (e.g., "iurc_search").
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
    perimeter: str = "Meta Infrastructure - LEAP District"
    region: str = "Lebanon, Indiana (Boone County)"
    assessment: str = ""


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Metabolism Pulse Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

class MetabolismPulse(BaseModel):
    """A point-in-time measurement of a resource grid (e.g., Power, Water).
    
    Attributes:
        resource: 'power', 'water', or 'wastewater'.
        value: The measured value.
        unit: 'MW' or 'MGD'.
        location: The geographic location.
        timestamp: When the measurement was taken.
    """
    type: Literal["MetabolismPulse"] = "MetabolismPulse"
    resource: str
    value: float = Field(ge=0.0)
    unit: str
    location: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Scout Result Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

class ScoutResult(BaseModel):
    """Top-level wrapper for all Probe output.

    Every probe execution produces a ProbeResult containing the typed
    intelligence payload, extracted entities, and suggested relationships.

    Attributes:
        probe_id: Identifier for the probe (e.g., "leap-probe-v1").
        source_url: The URL that was probed.
        timestamp: When the probe executed (UTC).
        intel: The typed intelligence payload.
        entities: Named entities extracted via the NER agentic pass.
        relationships: Suggested relationship edges between entities.
        raw_markdown_length: Length of the source content (for audit trail).
    """

    probe_id: str
    source_url: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    intel: Union[LEAPDistrictIntel, MetabolismPulse]
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relationships: list[RelationshipEdge] = Field(default_factory=list)
    raw_markdown_length: int = Field(default=0, ge=0)


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Chronicle Multi-Sig Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

class SealProof(BaseModel):
    """An individual outpost seal within a Multi-Sig proofs list.
    
    Attributes:
        verificationMethod: The outpost's Ed25519 public key.
        seal: The hex-encoded seal.
        outpost_id: The sovereign identifier (0x...).
        timestamp: When this seal was added.
    """
    type: str = "Ed25519Seal2026"
    verificationMethod: str
    seal: str
    outpost_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Chronicle Entry Payload Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

class ChronicleEntryPayload(BaseModel):
    """Validated data bundle for create_entry().

    This is the final gate before an intelligence entry gets sealed
    and appended to the JSON-LD Public Chronicle.

    Attributes:
        data: The typed intelligence payload (serialized to dict).
        source_url: Origin URL.
        probe_id: Probe that discovered the data.
        status: Entry verification status.
        entities: Entities to MERGE into Neo4j.
        relationships: Relationship edges to MERGE into Neo4j.
    """

    data: dict  # from intel.model_dump()
    source_url: str
    probe_id: str = "genesis"
    status: Literal["speculative", "pending_verification", "verified"] = (
        "speculative"
    )
    rep_g: int = Field(default=0, ge=0)
    gravity: int = Field(default=0, ge=0)
    evidence_cid: str = Field(default="")
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relationships: list[RelationshipEdge] = Field(default_factory=list)
    signatures: list[SealProof] = Field(default_factory=list)


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Operational Agenda (Sprint 10) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

class InterestProfile(BaseModel):
    """The user's investigative focus, extracted via Socratic dialogue.
    
    Attributes:
        perimeters: Sectors of interest (e.g., "Aviation", "LEAP District").
        keywords: High-resolution search terms.
        entities: Specific players or corporations to track.
        thresholds: Surprise index criteria (0-100).
        last_updated: Timestamp of the last Socratic session.
    """
    perimeters: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    entities: List[str] = Field(default_factory=list)
    thresholds: Dict[str, float] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BriefEntry(BaseModel):
    """A synthesized finding for a periodical brief."""
    title: str
    summary: str
    confidence: float
    source: str
    cid: str

class PeriodicalBrief(BaseModel):
    """The machine-readable JSON digest of the Chronicle findings."""
    start_time: datetime
    end_time: datetime
    findings: List[BriefEntry] = Field(default_factory=list)
    friction_report: List[str] = Field(default_factory=list) # Firewall activity
