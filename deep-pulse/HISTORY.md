# Deep Pulse: Historical Changelog

## [v0.1.0-alpha] - Sprint 1 (2026-04)
### Added
- **AutoDream Curiosity Bot**: Recursive loop intelligence discovery (`src/scouts/base_scout.py`).
- **Phase 0 Reconnaissance**: Implemented `BraveDiscovery` inside `pulse.py onboard`. Autonomously queries `api.search.brave.com` when the human operator provides empty targets, effectively generating "Genesis Points".
- **Truth Economy (REP-G)**: Staking and compute tracking (`src/core/economy.py`).
- **RLM Memory module**: Added hypothesis logging and dream paths (`db/memory.sqlite`). Placed patches for `metadata_json` logging (`src/core/memory.py`).
- **Socratic Onboarding**: Interactive CLI tool utilizing prompts to generate targeted `.yaml` perimeter config files globally.
- **Sovereign Cost Shield / RAG**: Embedded HTTP bridge to local models (e.g., `qwen2:0.5b`) to prevent Cloud LLM budget bleeding (`src/core/config.py`).
- Preflight setup scripts enforcing dependency validation (`src/scripts/preflight.py`).

### Changed
- Rebuilt `README.md` to establish the interactive Socratic Onboarding as the default `Quick Start` initialization flow.
- Upgraded target structures to skip restrictive UI gateways (e.g., bypassing `iurc.in.gov` SSL limits in favor of direct Search Portals).
- Configured Crawl4AI to use local `BrowserConfig` for evasion (`ignore_https_errors=True`, `enable_stealth=True`, realistic `user_agent`) rather than deprecated `CrawlerRunConfig` magic keyword maps.

### Fixed
- Fixed Python `ModuleNotFoundError: src` inside CLI modules by appending local paths to `sys.path`.
- Fixed `requirements.txt` invalid packages locking up `.venv` builds (`py-libp2p`, `sqlite3`, `argparse`, `asyncio`).
- Fixed DataDome and Playwright blockages by overriding default headless headers.

## [v0.2.0-alpha] - Sprint 2 (2026-04)
### Added
- **Tor-Aware Gossip Socket**: Zero-dependency `asyncio` networking with manual SOCKS5 negotiation (`src/swarm/gossip.py`).
- **Deep Ledger Protocol v1.0**: Standardized CID hashing (Multihash SHA-256) and ED25519 signatures (`docs/protocol.md`).
- **Peer Health & .Onion Rotation**: Logic for maintainance of signal integrity across latent Tor circuits (`src/swarm/peer.py`).
- **Consensus Verification**: 2+1 Proof of Audit engine (`src/swarm/verification.py`).

## [v0.3.0-alpha] - Sprint 3 (2026-04)
### Added
- **Dynamic Error Control (DEC)**: 3-tier "Immune System" for self-repairing obsolete/auth-expired endpoints (`src/scouts/base_scout.py`).
- **Architect Swarm**: Automated "Initiation Gap" pipeline to discover and blueprint modernized APIs (`src/architects/`).
- **Circuit Breaker**: Physical safety clamp to prevent compute-budget bleeding on hallucinated 200s (`src/core/breaker.py`).
- **Sensor Standard (SpiderFoot)**: Plug-and-Play OSINT correlation modules for 200+ data sources (`src/scouts/sensors/`).
- **Agent Orchestrators**: Head of Intel, Agent Manager, and Reporter Agent (`src/orchestration/`).
- **Deterministic Orchestration (LangChain/LangGraph)**: Implemented `src/core/chains.py` to define strict state machines for the Architect Swarm (Error -> Recon -> Schema -> Gate).
- **Global Ontology**: Seeded keyword-to-sensor mapping for decentralized discovery (`library/ontology.yaml`).

## [v0.4.0-alpha] - Sprint 4 (2026-04)
### Added
- **AI Ledger Analyst**: Created `src/core/analyst.py` for high-level pattern correlation across the Gossip mesh.
- **Indelible Audit Log**: Implemented `src/core/audit.py` with Ed25519-signed hash chains for tamper-evident activity tracking.
- **Specialist Perimeters**: Added production-ready intelligence perimeters for Infrastructure, Environment, and Maritime sectors.

## [v0.5.0-alpha] - Sprint 5 (2026-04)
### Added
- **Anonymity Architecture**: Established 3-layer separation (Human, Node, Profile) to maintain "Invisible Investigator" status.
- **Navigator Profile**: Introduced `templates/navigator_profile.yaml` for local-only interest mapping, stripped of identifiable capabilities.
- **Subscription Manifest**: Implemented Interest CID broadcasting in `src/swarm/gossip.py` to allow anonymous data prioritization.
- **REP-G (Reputation-Gossip)**: Reformed the reputation system in `src/core/economy.py` to be performance-based with a Sybil resistance threshold of 5 REP-G.
- **CLI Interest Broadcast**: Added `broadcast-interests` command to `src/pulse.py` to publish local interests to the swarm.
- **LangGraph State Persistence**: Integrated `Checkpointer` for long-running multi-step agent workflows in `src/core/chains.py`.

## [v0.7.0-alpha] - Sprint 7 (2026-04)
### Added
- **Post-Mission Debrief**: Implemented automated JSON summary generation at the end of every scout run (`data/history/`).
- **Heuristic Feedback Loop**: Added `debrief_scout()` to `AgentManager` (`src/core/manager.py`) to parse scout results and update search patterns.
- **RLM Global Heuristics**: Created `data/heuristics/global_ledger.yaml` to persist "Preferred Paths" (Pattern Recognition) and "Avoid Paths" (Blacklist/Efficiency).
- **USD Budget Tracking**: Integrated session cost logging against the $2.00 compute limit defined in perimeter configs.
- **Dynamic Config Updates**: Managing Agent now automatically injects "Verified Discovery" targets back into mission `.yaml` files.
- **Stealth Scan Enhancements**: Implemented User-Agent rotation (Chrome/Linux) and standard browser header spoofing in `WebScout` to bypass Akamai/WAF blocks. Added random jitter (2-5s) in `BaseScout` to mimic human browsing.
- **Universal Document Support**: `WebScout` now detects `type: document` or `.pdf` suffixes to trigger specialized PDF-to-Markdown extraction via Crawl4AI.

### Changed
- Moved `AgentManager` from `src/orchestration/manager.py` to `src/core/manager.py` to center the intelligence feedback loop in the core logic.

## [v0.8.0-alpha] - Sprint 8 (2026-04)
### Added
- **Scope 3 Ghost Audit**: High-resolution mission (`scope3_ghost_audit_2026`) for maritime logistics carbon intensity.
- **Session Priming support**: Added `prime_url` logic to `WebScout` to establish browser sessions/cookies before deep scraping (e.g., for `polb.com`).
- **Truth Synthesis Specialization**: Added `LedgerAnalyst` logic to decouple Net Zero marketing from bunker fuel reality using 75 gCO2e/MJ thresholds.
- **SB 253 'Safe Harbor' Detection**: Implemented heuristic detection of corporate hedging via "methodological uncertainty" citations in Scope 3 disclosures.
- **Integrated Browser Subagent**: Successfully utilized browser-level automation to extract granular manifest totals (97,422 TEUs) from Port of Long Beach February 2026 reports.

### Changed
- Improved `WebScout` stealth warm-up to handle custom navigation targets before mission-critical data extraction.
