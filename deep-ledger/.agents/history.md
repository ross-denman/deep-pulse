# Deep Ledger — The Mental Lighthouse

> A living record of every sprint, decision, and lesson learned.

---

## Genesis — Project Bootstrap
**Date**: 2026-04-04
**Objective**: Initialize the Deep Ledger infrastructure — the immutable backbone for the Deep Pulse Intelligence Swarm.
**Key Decisions**:
- **Identity**: Ed25519 keypair generated at bootstrap. Public key = Node ID `0x0001`. Private key stored in `.env` (git-ignored).
- **LLM Provider**: OpenRouter (free tier) via `OPENROUTER_API_KEY`. Configurable per-node.
- **Ledger Format**: JSON-LD (`harvest/ledger.jsonld`) with Deep Ledger Intelligence Standard v1.0.
- **First Perimeter**: LEAP District — Meta's $10B Infrastructure Expansion in Lebanon, Indiana.
- **First Scout Target**: IURC Annual Report filings + Boone County Water Variance docs.
- **Stack**: Python 3.12, Neo4j, Crawl4AI, libp2p, LangGraph.
- **Interface**: CLI "Command Bridge" primary. Streamlit HUD as optional plugin.
**Technical Debt/TODOs**:
- OrbitDB integration deferred to Sprint 02.
- P2P libp2p networking deferred to Sprint 03.
- Streamlit HUD deferred to Sprint 04.
