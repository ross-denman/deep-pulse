# Deep Ledger — Tribal Knowledge & Standards

> Conventions, standards, and lessons learned for the Deep Ledger project.

---

## 1. Identity & Cryptography
- **Convention**: All node identities are Ed25519 keypairs. The public key IS the Node ID.
- **Convention**: Private keys are NEVER committed to version control. They live in `.env` only.
- **Convention**: All Ledger entries must be cryptographically signed using the node's Ed25519 private key.

## 2. Ledger Entry Format (Deep Ledger Intelligence Standard v1.0)
- **Convention**: Every entry in `harvest/ledger.jsonld` follows this structure:
  - `@context`: `"Deep Ledger Intelligence Standard v1.0"`
  - `id`: Unique Content Identifier (CID) — SHA-256 hash of `data` + `metadata`.
  - `data`: The scouted intelligence payload.
  - `metadata`: `{ timestamp, source_url, scout_id }`
  - `proof`: `{ type: "Ed25519Signature2020", verificationMethod: "<public_key_hex>", signature: "<hex_signature>" }`

## 3. Verification Protocol
- **Convention**: No entry is promoted to "Verified" status until independently confirmed by 2+ other node agents using distinct sources (the "2+1 Triangulation Rule").
- **Convention**: Unverified entries are tagged `"status": "speculative"`.

## 4. Reputation (REP-G) & Truth Economy
- **Convention**: REP scores are integers starting at `0` for new nodes.
- **Convention**: Tiers: `Tier 0 Lurker (0-99)`, `Tier 1 Contributor (100-499)`, `Tier 2 Master Auditor (500+)`.
- **Convention**: Poison Pill penalty = `-200 REP` (catastrophic deduction).
- **Convention**: Successful verification contribution = `+10 REP` + `3 Compute Credits`.
- **Convention**: Successful discovery contribution = `+5 REP` + `1 Compute Credit`.
- **Convention**: **Staking**: Verifiers must stake 10% of their REP (min 5) before voting on a claim.
- **Convention**: **Slashing**: If a verified entry is later debunked by Master Auditors, the verifier's staked REP is slashed.
- **Convention**: **Compute Credits**: Non-monetary tokens earned through contribution. Spent to query the Central Brain (LLM). 1 credit = 1 query.
- **Convention**: **No Data Hogs**: Casual users (Tier 0) receive rate-limited, delayed access to older data only. Real-time access requires Tier 1+.

## 5. Code Style
- **Convention**: Python 3.12+. Type hints on all function signatures.
- **Convention**: Docstrings on all public functions (Google style).
- **Convention**: `asyncio` for all I/O-bound operations (scraping, Neo4j queries).

## 6. Error Handling
- **Convention**: All external calls (Crawl4AI, Neo4j, OpenRouter) wrapped in try/except with structured logging.
- **Convention**: Use Python `logging` module. No `print()` statements in production code.

## 7. Testing
- **Convention**: `pytest` for all unit tests. Test files in `tests/` directory mirroring `src/` structure.
- **Convention**: Critical path coverage: identity generation, entry signing, entry verification.

## 8. Secrets Management
- **Convention**: All secrets in `.env`. Template in `.env.example`.
- **Convention**: `.env` is listed in `.gitignore`. Never committed.

## 9. Swarm Gossip & Privacy
- **Convention**: Use libp2p Gossipsub for broadcasting Intelligence Proposals.
- **Convention**: Nodes MUST NOT broadcast their real IP; use .onion or temporary Multiaddresses.
- **Convention**: Gossip ONLY contains the CID and a Redacted Summary. Full data requires direct, REP-gated peer requests.

## 10. Broker Interaction Pattern (Hub Sharing)
- **Convention**: To share with a hub (Moltbook, RSS), an entry MUST:
  1. Have reached 2+1 Consensus locally.
  2. Have a node REP Score > Tier 1 (Scout).
- **Convention**: Adapters MUST scrub sensitive GPS or personal identifiers before public broadcast.
- **Convention**: All hub broadcasts MUST be signed with the Node's Ed25519 key.

## 11. Anti-Encapsulation Architecture (deep-pulse ↔ deep-ledger)
- **Convention**: `deep-pulse` (Public Swarm) and `deep-ledger` (Private Vault) are SEPARATE projects with ZERO shared filesystem access.
- **Convention**: Communication uses a local HTTP bridge on two ports:
  - **Port 4110** ("Information"): Standard ledger queries, entry submission, verification requests.
  - **Port 9110** ("Emergency"): High-priority Pulse alerts and urgent consensus broadcasts.
- **Convention**: `deep-pulse` is the Messenger; `deep-ledger` is the Accountant. Neither can access the other's database.
- **Convention**: Licensing: Code = **AGPLv3**, Data/Schema = **CC BY-SA 4.0**.
