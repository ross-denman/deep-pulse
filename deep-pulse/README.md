# 📡 Deep Pulse — The P2P Intelligence Swarm

> "Truth is the only commodity."

Deep Pulse is the public, decentralized messenger for the Deep Ledger ecosystem. It is a swarm of autonomous agents (Scouts) and human-in-the-loop nodes that verify, gossip, and report on high-integrity intelligence.

## 🏗️ Architecture: Anti-Encapsulation
Deep Pulse is designed with strict **Anti-Encapsulation**. It is SEPARATE from your private vault (**Deep Ledger**). 
- **Deep Pulse** = The Messenger (Public Swarm)
- **Deep Ledger** = The Accountant (Private Vault)

Communication happens via a local-only bridge on **Port 4110** (Info) and **Port 9110** (Emergency).

## 🧠 Key Features
- **Sprint 01: The Lone Wolf**
  - **AutoDream Curiosity Bot**: Autonomous research recursive loops with "Hunch" generation.
  - **Sovereign Cost Shield**: Local SLM distillation (Ollama) to protect cloud API budgets.
  - **Socratic Onboarding**: Conversational CLI for defining mission perimeters.

- **Sprint 02: Swarm Synapse (P2P Mesh)**
  - **Tor-Aware Gossip Socket**: Zero-dependency `asyncio` networking with manual SOCKS5 negotiation.
  - **Deep Ledger Protocol v1.0**: Standardized CID hashing (Multihash SHA-256) and ED25519 signatures.
  - **Peer Health & .Onion Rotation**: Logic for maintainance of signal integrity across latent Tor circuits.

- **Sprint 03: The Architect Swarm**
  - **Dynamic Error Control (DEC)**: 3-tier "Immune System" for self-repairing obsolete/auth-expired endpoints.
  - **Architect Swarm**: Automated "Initiation Gap" pipeline to discover and blueprint modernized APIs.
  - **Circuit Breaker**: Physical safety clamp to prevent compute-budget bleeding on hallucinated 200s.
  - **Sensor Standard (SpiderFoot)**: Plug-and-Play OSINT correlation modules for 200+ data sources.

- **Sprint 04: Hub Expansion**
  - **AI Ledger Analyst**: Pattern recognition and correlation engine for cross-mesh intelligence.
  - **Indelible Audit Log**: Ed25519-signed, append-only tamper-evident hash chain.
  - **Specialist Perimeters**: Focused YAML configs for Infrastructure, Maritime, and Environment.

- **Sprint 05: The Invisible Investigator (Anonymity & Reputation)**
  - **Anonymity Architecture**: 3-layer separation (Human/Node/Profile) for investigator privacy.
  - **Subscription Manifest**: Interest CID broadcasting to prioritize Gossip pushes anonymously.
  - **REP-G (Reputation-Gossip)**: Performance-based reputation with Sybil resistance.
  - **Anonymous Profile**: Stripped `navigator_profile.yaml` focusing on interests over identity.

- **Sprint 07: The Intelligent Manager (Heuristic Feedback Loop)**
  - **Post-Mission Debrief**: Automated JSON summary generation at the end of every scout run (`data/history/`).
  - **Heuristic Feedback Loop**: `debrief_scout()` in `AgentManager` (`src/core/manager.py`) to parse scout results and update search patterns.
  - **RLM Global Heuristics**: Persistence of Preferred/Avoid paths in `global_ledger.yaml`.
  - **Budget Tracking**: Mission-specific cost logging against USD limits ($2.00 default).

- **Sprint 08: Operational Readiness & Truth Synthesis** ✅
  - **Session Priming**: `prime_url` support in `WebScout` to establish browser sessions before deep scraping.
  - **Scope 3 Ghost Audit**: High-resolution specialized logic for maritime carbon intensity and SB 253 "Safe Harbor" detection.
  - **Adaptive Proxy Logic**: Stealth bypass for Federal targets to avoid exit-node blacklisting.
  - **LocalScout Template**: Manual ingest system for protected PDFs using `data/local_ingest/`.

- **Sprint 09: Deep Navigator (Structural Intelligence)** ✅
  - **Surprise-to-Action (S2A)**: "Deep Dive" trigger that automatically initiates sub-scouting (About Us/Manufacturer) upon anchor detection.
  - **Modular Specialist Plugins**: External YAML heuristics for domain-specific Truth Synthesis (Health, Legal, Maritime).
  - **Stealth Pre-Scout**: Automatic probing of ToS/Disclaimer sub-portals before claim extraction.
  - **Batch Settlement (Genesis Signature)**: Integrated bridge to Deep Ledger for signing and "minting" multi-mission truth pulses.
  - **Operational Autonomy**: Implemented `auto_approve_schema_drift` and Environment Pre-flight checks.

## ⚖️ The Truth Economy (REP-G)
- **Reputation (REP)**: Earned by auditing claims. No traditional crypto.
- **Staking**: Verifiers must stake REP to audit a claim.
- **Slashing**: Lying or getting debunked by Master Auditors results in a REP slash.
- **Compute Credits**: Earned by contributing, spent to query the Central Brain (LLM).

## 🚀 Quick Start
```bash
# 1. Setup environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 1.5 Configure API Keys (Add to .env)
# BRAVE_API_KEY=your_brave_key_here  (Required for autonomous Discovery/Genesis phase)
# OPENROUTER_API_KEY=your_key_here   (Optional, Perplexity MCP for later)

# 2. Socratic Onboarding (Create your Mission & Identity)
python3 src/pulse.py onboard

# 3. Start a Scout (Use your generated config, or pre-built ones)
python3 src/pulse.py scout run --template web --config templates/perimeters/infrastructure.yaml
```
*Note: Deep Pulse includes several pre-configured perimeters in `templates/perimeters/` (e.g., `infrastructure.yaml`, `crypto.yaml`, `sports.yaml`) that you can leverage without needing to run the interactive onboarding.*


## 📚 Documentation & Status
- **Roadmap**: [Deep Pulse Roadmap](deep-pulse-roadmap.md)
- **Developer Guidelines**: [Coding Conventions](docs/conventions.md)
- **Changelog**: [Version History](HISTORY.md)

## 📜 Licensing
- **Code**: [AGPLv3](LICENSE)
- **Data/Schema**: [CC BY-SA 4.0](LICENSE-DATA)
