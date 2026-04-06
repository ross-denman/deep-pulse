// ─── Deep Ledger — Neo4j Knowledge Graph Schema ───
// Run this file against your Neo4j instance to initialize constraints and indexes.
// Usage: cat src/db/schema.cypher | cypher-shell -u neo4j -p <password>

// ═══════════════════════════════════════════════════
// CONSTRAINTS
// ═══════════════════════════════════════════════════

// Node Identity — Every agent node has a unique ID
CREATE CONSTRAINT node_id_unique IF NOT EXISTS
FOR (n:Node) REQUIRE n.node_id IS UNIQUE;

// Intelligence Entry — Every entry has a unique CID
CREATE CONSTRAINT entry_cid_unique IF NOT EXISTS
FOR (e:IntelligenceEntry) REQUIRE e.cid IS UNIQUE;

// Entity — Named entities extracted from intelligence
CREATE CONSTRAINT entity_name_unique IF NOT EXISTS
FOR (ent:Entity) REQUIRE ent.name IS UNIQUE;

// ═══════════════════════════════════════════════════
// INDEXES
// ═══════════════════════════════════════════════════

CREATE INDEX node_reputation IF NOT EXISTS
FOR (n:Node) ON (n.reputation_score);

CREATE INDEX entry_status IF NOT EXISTS
FOR (e:IntelligenceEntry) ON (e.status);

CREATE INDEX entry_timestamp IF NOT EXISTS
FOR (e:IntelligenceEntry) ON (e.timestamp);

CREATE INDEX entry_perimeter IF NOT EXISTS
FOR (e:IntelligenceEntry) ON (e.perimeter);

CREATE INDEX entity_type IF NOT EXISTS
FOR (ent:Entity) ON (ent.entity_type);

// ═══════════════════════════════════════════════════
// NODE SCHEMA (Properties)
// ═══════════════════════════════════════════════════
// 
// (:Node {
//   node_id: STRING,           -- e.g. "0x0001abcd..."
//   public_key_hex: STRING,    -- Ed25519 public key
//   reputation_score: INTEGER, -- Current REP score
//   tier: INTEGER,             -- 0, 1, or 2
//   alias: STRING,             -- Human-readable name
//   created_at: DATETIME,
//   last_active: DATETIME
// })
//
// (:IntelligenceEntry {
//   cid: STRING,               -- Content Identifier (SHA-256)
//   type: STRING,              -- e.g. "LEAPDistrictIntel", "GenesisEntry"
//   title: STRING,
//   status: STRING,            -- "speculative", "pending_verification", "verified"
//   perimeter: STRING,         -- Intelligence Perimeter
//   source_url: STRING,
//   scout_id: STRING,
//   timestamp: DATETIME,
//   signature: STRING          -- Ed25519 signature hex
// })
//
// (:Entity {
//   name: STRING,              -- e.g. "Meta Platforms", "IURC", "Boone County"
//   entity_type: STRING,       -- "Corporation", "Agency", "Location", "Project"
//   description: STRING
// })
//
// (:ReputationEvent {
//   event_type: STRING,        -- "discovery", "verification", "poison_pill", etc.
//   points: INTEGER,
//   reason: STRING,
//   timestamp: DATETIME,
//   related_cid: STRING
// })

// ═══════════════════════════════════════════════════
// RELATIONSHIP TYPES
// ═══════════════════════════════════════════════════
//
// (:Node)-[:DISCOVERED]->(:IntelligenceEntry)
// (:Node)-[:VERIFIED]->(:IntelligenceEntry)
// (:Node)-[:HAS_REPUTATION_EVENT]->(:ReputationEvent)
// (:IntelligenceEntry)-[:MENTIONS]->(:Entity)
// (:IntelligenceEntry)-[:RELATED_TO]->(:IntelligenceEntry)
// (:Entity)-[:LINKED_TO]->(:Entity)
// (:Entity)-[:LOCATED_IN]->(:Entity)
// (:Entity)-[:EXCEEDS]->(:Entity)    -- e.g., usage exceeds limits

// ═══════════════════════════════════════════════════
// SEED DATA — LEAP District Entities
// ═══════════════════════════════════════════════════

MERGE (meta:Entity {name: "Meta Platforms"})
SET meta.entity_type = "Corporation",
    meta.description = "Parent company of Facebook. Building 1GW data center campus in Lebanon, IN.";

MERGE (leap:Entity {name: "LEAP District"})
SET leap.entity_type = "Project",
    leap.description = "Lebanon Advancement & Progress District — Meta's $10B data center expansion site.";

MERGE (iurc:Entity {name: "IURC"})
SET iurc.entity_type = "Agency",
    iurc.description = "Indiana Utility Regulatory Commission — regulates public utilities in Indiana.";

MERGE (boone:Entity {name: "Boone County"})
SET boone.entity_type = "Location",
    boone.description = "County in Indiana where Lebanon is located. Site of Meta's data center.";

MERGE (lebanon:Entity {name: "Lebanon, Indiana"})
SET lebanon.entity_type = "Location",
    lebanon.description = "City in Boone County, IN. Home to the LEAP District.";

MERGE (hb1245:Entity {name: "HB 1245"})
SET hb1245.entity_type = "Legislation",
    hb1245.description = "Indiana bill requiring IURC to study rate impact of data centers on residential users by October 2026.";

// Relationships between seed entities
MERGE (meta)-[:BUILDING]->(leap)
MERGE (leap)-[:LOCATED_IN]->(lebanon)
MERGE (lebanon)-[:LOCATED_IN]->(boone)
MERGE (hb1245)-[:REGULATES]->(meta)
MERGE (iurc)-[:OVERSEES]->(hb1245)
MERGE (iurc)-[:MONITORS]->(leap);
