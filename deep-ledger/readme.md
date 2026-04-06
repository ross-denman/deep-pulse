# Deep Ledger

> **The Immutable Infrastructure for the Deep Pulse Intelligence Swarm**

Deep Ledger is the verifiable, decentralized backbone for **Deep Pulse** — a P2P AI-driven intelligence swarm. It transforms raw, autonomous discovery into high-integrity, structured intelligence. Designed to operate across information blackouts and censorship, it provides a "Ground Truth" record of resource movements, infrastructure shifts, and big-money maneuvers.

---

## 🔑 Core Principles

| Principle | Description |
| :--- | :--- |
| **Sovereign Identity** | Every node is an Ed25519 keypair. Your public key IS your identity. |
| **Consensus-as-Truth** | No data is "fact" until independently verified by 2+ other nodes (2+1 Triangulation). |
| **Reputation-as-Gateway (REP-G)** | Access to the Knowledge Graph is gated by your contribution score. |
| **Zero Trust** | No node is trusted by default. Information is "Speculative" until consensus. |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                 COMMAND BRIDGE (CLI)                 │
│          python src/bridge.py <command>              │
├─────────────┬───────────────┬───────────────────────┤
│  IDENTITY   │    LEDGER     │     REPUTATION        │
│  Ed25519    │  JSON-LD      │     REP-G Protocol    │
│  Sign/Verify│  CID Hashing  │     Tier 0/1/2        │
├─────────────┴───────────────┴───────────────────────┤
│              SCOUT AGENTS                           │
│  LEAP Scout → IURC / Boone County / HB 1245        │
├─────────────────────────────────────────────────────┤
│            NEO4J KNOWLEDGE GRAPH                    │
│  Entities ←→ Relationships ←→ Intelligence Entries  │
└─────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate your sovereign identity
python src/core/identity_generator.py

# 3. Create Genesis entry
python src/bridge.py onboard

# 4. Check status
python src/bridge.py status

# 5. Deploy LEAP scout
python src/bridge.py scout --target leap

# 6. View Ledger
python src/bridge.py ledger --tail 10
```

## 📡 Current Intelligence Perimeters

### LEAP District (Meta Infrastructure)
- **Signal**: Meta has broken ground on a 1-gigawatt campus in Lebanon, Indiana.
- **Alpha**: Indiana bill HB 1245 requires IURC to study rate impact by October 2026.
- **Scout Targets**: IURC Annual Reports, Boone County Water Variance docs.

## 📁 Project Structure

```
deep-ledger/
├── .agents/              # Agent intelligence (sprints, history, conventions)
├── docs/                 # Reference documentation
├── harvest/              # Ledger output (JSON-LD)
│   └── ledger.jsonld     # The Immutable Ledger
├── src/
│   ├── agents/           # Scout agents
│   │   └── leap_scout.py # LEAP District crawler
│   ├── core/             # Core engine
│   │   ├── identity.py   # Ed25519 identity management
│   │   ├── ledger.py     # JSON-LD signing & CID generation
│   │   ├── consensus.py  # 2+1 Verification Triangle
│   │   └── reputation.py # REP-G Protocol
│   ├── db/               # Neo4j schema & queries
│   └── bridge.py         # CLI entry point
├── tests/                # Test suite
└── docker-compose.yml    # Neo4j infrastructure
```

## 🔐 Ledger Entry Format (Deep Ledger Intelligence Standard v1.0)

```json
{
  "@context": "Deep Ledger Intelligence Standard v1.0",
  "id": "cid:<SHA-256 hash>",
  "data": { "...scouted intelligence..." },
  "metadata": {
    "timestamp": "2026-04-04T20:00:00Z",
    "source_url": "https://...",
    "scout_id": "leap-scout-v1"
  },
  "proof": {
    "type": "Ed25519Signature2020",
    "verificationMethod": "<public_key_hex>",
    "signature": "<hex_signature>"
  }
}
```

## Project History
See [.agents/history.md](.agents/history.md) for a summary of all completed sprints.
