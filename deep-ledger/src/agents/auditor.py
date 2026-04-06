#!/usr/bin/env python3
"""
Deep Ledger — Internal Auditor (LLM-Based NER)

The Agentic Pass: processes raw scouted Markdown through an LLM
(via OpenRouter) to extract structured entities and relationships.

Flow:
    1. Receives raw markdown + keyword context from the Scout.
    2. Sends a structured prompt requesting JSON extraction.
    3. Parses the LLM response into ExtractedEntity + RelationshipEdge models.
    4. Falls back to keyword-only extraction if LLM is unavailable.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.core.models import ExtractedEntity, RelationshipEdge

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# ─── Valid Enums (for the LLM prompt) ────────────────────────────

ENTITY_TYPES = [
    "Corporation", "Agency", "Location", "Project",
    "Legislation", "Resource", "Person", "Organization",
]

RELATIONSHIP_TYPES = [
    "MENTIONS", "CONSUMES", "REGULATES", "LOCATED_IN", "LINKED_TO",
    "BUILDING", "OVERSEES", "MONITORS", "EXCEEDS", "SUPPLIES",
    "FUNDS", "OPPOSES", "SUPPORTS",
]

# ─── System Prompt ──────────────────────────────────────────────

SYSTEM_PROMPT = """You are an intelligence analyst for the Deep Pulse Intelligence Swarm.
Your job is to extract named entities and their relationships from raw scouted content.

ENTITY TYPES (use exactly these):
{entity_types}

RELATIONSHIP TYPES (use exactly these):
{relationship_types}

CONTEXT: This intelligence relates to the LEAP District — Meta Platforms' $10B data center
campus in Lebanon, Indiana (Boone County). Key actors include Meta Platforms, IURC
(Indiana Utility Regulatory Commission), Boone County government, and Indiana legislators.

Respond ONLY with valid JSON in this exact format:
{{
  "entities": [
    {{
      "name": "Entity Name",
      "entity_type": "Corporation",
      "description": "Brief description of relevance",
      "confidence": 0.95
    }}
  ],
  "relationships": [
    {{
      "source": "Entity A Name",
      "target": "Entity B Name",
      "relationship_type": "CONSUMES",
      "context": "Why this relationship exists",
      "confidence": 0.85
    }}
  ]
}}

Rules:
- Extract ALL named entities you can identify (companies, agencies, locations, etc.)
- Only suggest relationships where you have evidence in the text
- Set confidence based on how explicitly the entity/relationship is stated
- Use canonical names (e.g., "Meta Platforms" not "Meta" or "Facebook")
- Do NOT hallucinate entities not present in the source text
""".format(
    entity_types=", ".join(ENTITY_TYPES),
    relationship_types=", ".join(RELATIONSHIP_TYPES),
)


class InternalAuditor:
    """LLM-based entity and relationship extractor.

    Uses OpenRouter (or any OpenAI-compatible API) to perform an
    Agentic NER Pass on scouted markdown content.

    Args:
        api_key: Override the OPENROUTER_API_KEY from .env.
        model: Override the LLM model from .env.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.model = model or os.getenv("MODEL", "openrouter/free")
        self.base_url = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")

    async def extract(
        self,
        markdown: str,
        keywords_matched: list[str] | None = None,
        target_description: str = "",
    ) -> tuple[list[ExtractedEntity], list[RelationshipEdge]]:
        """Extract entities and relationships from scouted markdown.

        Args:
            markdown: The raw scouted content.
            keywords_matched: Keywords that triggered this extraction.
            target_description: Description of the scout target.

        Returns:
            Tuple of (entities, relationships).
        """
        # Try LLM extraction first
        if self.api_key:
            try:
                return await self._llm_extract(
                    markdown, keywords_matched, target_description
                )
            except Exception as e:
                logger.warning(
                    "LLM extraction failed, falling back to keyword mode: %s", e
                )

        # Fallback: keyword-based extraction
        return self._keyword_extract(markdown, keywords_matched or [])

    async def _llm_extract(
        self,
        markdown: str,
        keywords_matched: list[str] | None,
        target_description: str,
    ) -> tuple[list[ExtractedEntity], list[RelationshipEdge]]:
        """Perform LLM-based entity extraction via OpenRouter.

        Args:
            markdown: Raw content to analyze.
            keywords_matched: Keywords that matched in the content.
            target_description: Scout target description.

        Returns:
            Tuple of (entities, relationships).
        """
        try:
            from openai import AsyncOpenAI
        except ImportError:
            logger.error("openai package not installed. Cannot run LLM extraction.")
            return self._keyword_extract(markdown, keywords_matched or [])

        # Truncate markdown to avoid token limits (keep most relevant content)
        max_chars = 6000
        truncated = markdown[:max_chars] if len(markdown) > max_chars else markdown

        user_prompt = (
            f"## Scout Target\n{target_description}\n\n"
            f"## Keywords Matched\n{', '.join(keywords_matched or [])}\n\n"
            f"## Source Content\n{truncated}\n\n"
            "Extract all entities and relationships from the above content."
        )

        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                logger.warning("LLM returned empty response.")
                return self._keyword_extract(markdown, keywords_matched or [])

            return self._parse_llm_response(content)

        except Exception as e:
            logger.error("OpenRouter LLM call failed: %s", e)
            raise

    def _parse_llm_response(
        self, raw_json: str
    ) -> tuple[list[ExtractedEntity], list[RelationshipEdge]]:
        """Parse and validate the LLM's JSON response.

        Args:
            raw_json: The raw JSON string from the LLM.

        Returns:
            Tuple of (entities, relationships).
        """
        entities: list[ExtractedEntity] = []
        relationships: list[RelationshipEdge] = []

        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as e:
            logger.error("LLM returned invalid JSON: %s", e)
            return entities, relationships

        # Parse entities with Pydantic validation
        for raw_entity in data.get("entities", []):
            try:
                entity = ExtractedEntity(**raw_entity)
                entities.append(entity)
            except Exception as e:
                logger.warning(
                    "Skipping invalid entity %s: %s",
                    raw_entity.get("name", "?"),
                    e,
                )

        # Parse relationships with Pydantic validation
        for raw_rel in data.get("relationships", []):
            try:
                edge = RelationshipEdge(**raw_rel)
                relationships.append(edge)
            except Exception as e:
                logger.warning(
                    "Skipping invalid relationship %s->%s: %s",
                    raw_rel.get("source", "?"),
                    raw_rel.get("target", "?"),
                    e,
                )

        logger.info(
            "LLM extraction: %d entities, %d relationships",
            len(entities),
            len(relationships),
        )
        return entities, relationships

    def _keyword_extract(
        self,
        markdown: str,
        keywords_matched: list[str],
    ) -> tuple[list[ExtractedEntity], list[RelationshipEdge]]:
        """Fallback: extract entities from keyword matches.

        This is the heuristic fallback when the LLM is unavailable.
        It maps known LEAP keywords to their canonical entity types.

        Args:
            markdown: The raw content.
            keywords_matched: Keywords that matched.

        Returns:
            Tuple of (entities, relationships).
        """
        # Known LEAP entity mapping (production seed data)
        keyword_entity_map: dict[str, dict[str, Any]] = {
            "meta": {
                "name": "Meta Platforms",
                "entity_type": "Corporation",
                "description": "Parent company of Facebook. Building 1GW data center campus in Lebanon, IN.",
            },
            "data center": {
                "name": "LEAP District",
                "entity_type": "Project",
                "description": "Lebanon Advancement & Progress District — Meta's $10B data center expansion site.",
            },
            "iurc": {
                "name": "IURC",
                "entity_type": "Agency",
                "description": "Indiana Utility Regulatory Commission — regulates public utilities in Indiana.",
            },
            "hb 1245": {
                "name": "HB 1245",
                "entity_type": "Legislation",
                "description": "Indiana bill requiring IURC to study rate impact of data centers by October 2026.",
            },
            "rate impact": {
                "name": "Rate Impact Study",
                "entity_type": "Project",
                "description": "IURC-mandated study on how data centers affect residential utility rates.",
            },
            "gigawatt": {
                "name": "LEAP District",
                "entity_type": "Project",
                "description": "Lebanon Advancement & Progress District — 1GW data center campus.",
            },
            "water variance": {
                "name": "Boone County Water Variance",
                "entity_type": "Resource",
                "description": "Water usage variance applications for the LEAP District data center campus.",
            },
            "boone county": {
                "name": "Boone County",
                "entity_type": "Location",
                "description": "County in Indiana where Lebanon is located. Site of Meta's data center.",
            },
            "lebanon": {
                "name": "Lebanon, Indiana",
                "entity_type": "Location",
                "description": "City in Boone County, IN. Home to the LEAP District.",
            },
        }

        entities: list[ExtractedEntity] = []
        seen_names: set[str] = set()

        for keyword in keywords_matched:
            key = keyword.lower()
            if key in keyword_entity_map:
                entity_data = keyword_entity_map[key]
                name = entity_data["name"]
                if name not in seen_names:
                    entities.append(
                        ExtractedEntity(
                            name=name,
                            entity_type=entity_data["entity_type"],
                            description=entity_data["description"],
                            confidence=0.7,  # Lower confidence for heuristic
                        )
                    )
                    seen_names.add(name)

        # Known LEAP relationships from seed data
        relationships: list[RelationshipEdge] = []
        entity_names = {e.name for e in entities}

        seed_edges = [
            ("Meta Platforms", "LEAP District", "BUILDING", "Meta is building the LEAP District campus"),
            ("LEAP District", "Lebanon, Indiana", "LOCATED_IN", "LEAP District is in Lebanon, IN"),
            ("Lebanon, Indiana", "Boone County", "LOCATED_IN", "Lebanon is in Boone County"),
            ("HB 1245", "Meta Platforms", "REGULATES", "HB 1245 mandates rate impact study for data centers"),
            ("IURC", "HB 1245", "OVERSEES", "IURC is responsible for the HB 1245 rate impact study"),
            ("IURC", "LEAP District", "MONITORS", "IURC monitors utility impact of LEAP District"),
        ]

        for source, target, rel_type, context in seed_edges:
            if source in entity_names and target in entity_names:
                relationships.append(
                    RelationshipEdge(
                        source=source,
                        target=target,
                        relationship_type=rel_type,
                        context=context,
                        confidence=0.8,
                    )
                )

        logger.info(
            "Keyword extraction fallback: %d entities, %d relationships",
            len(entities),
            len(relationships),
        )
        return entities, relationships
