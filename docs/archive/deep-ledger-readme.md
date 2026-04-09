# 📜 Deep Ledger: The Public Chronicle
### *The Physical Anchor for Distributed Intelligence*

The **Public Chronicle** is a sovereign, decentralized framework for the automated discovery and settlement of structured intelligence. It transforms raw, autonomous data acquisition from the **Discovery Mesh** into a high-integrity, immutable record of institutional shifts, resource allocations, and regulatory maneuvers.

## 🔑 Core Principles

| Principle | Description |
| :--- | :--- |
| **Physical Anchor** | The chronicle is more than data; it is an anchored history with a self-documenting Genesis Header. |
| **Consensus-as-Truth** | Intelligence is not settled until independently verified through the 2+1 Triangulation protocol. |
| **The Grains Protocol** | User reputation and access tiering are governed by the meritocratic distribution of Grains ($REP-G). |
| **Zero Trust Auditing** | All incoming signals are quarantined as "Speculative" until consensus is mathematically achieved. |

## 🏗️ Technical Architecture (The Auditor)

The Auditor core is responsible for the validation and settlement of all truth pulses.

- **Identity Layer**: Ed25519-based "Sovereign Identity" where every outpost is a unique keypair.
- **Settlement Engine**: Processes incoming `ProbeResult` objects, validates seals, and merges them into the chronicle.
- **Knowledge Graph**: A persistent Neo4j instance that map "Entities" and "Relationships" from the settled chronicle.

## 🚀 Operations (Bridge CLI)

```bash
# 1. Initialize environment
pip install -r requirements.txt

# 2. Generate outpost identity
python src/core/identity_generator.py

# 3. Initialize authoritative bridge (Auditor Only)
python src/bridge.py onboard

# 4. View Settled Chronicle
python src/bridge.py chronicle --tail 25

# 5. Reconstruct Graph from Archive
python src/db/rebuild_graph.py --chronicle harvest/chronicle.jsonld
```

## 🔐 Data Standard (Intelligence Standard v1.2)

The chronicle uses a multi-sig JSON-LD format to ensure immutable provenance.

```json
{
  "@context": "Discovery Mesh Intelligence Standard v1.2",
  "id": "cid:<SHA-256 hash>",
  "data": { "...structured discovery payload..." },
  "metadata": {
    "timestamp": "2026-04-06T12:00:00Z",
    "source_url": "https://...",
    "probe_id": "probe-v1-alpha"
  },
  "proof": {
    "type": "MultiSignature2026",
    "signatures": [
      {
        "verificationMethod": "<public_key_hex>",
        "seal": "<hex_seal>",
        "outpost_id": "0x...",
        "timestamp": "..."
      }
    ]
  }
}
```

## 📁 Internal Structure

```
deep-ledger/
├── docs/                 # Technical specs & Lexicon
├── harvest/              # The Physical Anchor
│   └── chronicle.jsonld     # THE PUBLIC CHRONICLE
├── src/
│   ├── core/             # Protocol & Consensus logic
│   │   ├── chronicle.py     # JSON-LD signing & CID generation
│   │   ├── consensus.py  # 2+1 Verification & Economy
│   │   ├── reputation.py # Grains Protocol ($REP-G)
│   │   └── security.py   # Auditor Bridge & Verification
│   ├── db/               # Knowledge Graph (Neo4j)
│   │   ├── driver.py     # Neo4j Async Driver
│   │   └── schema.cypher  # Graph Constraints
│   └── bridge.py         # Auditor Management CLI
└── docker-compose.yml    # Graph Infrastructure (Neo4j)
```

---
**Standard**: MultiSignature2026
**Storage**: JSON-LD / Neo4j
**Role**: Authoritative Archive
