# Deep Pulse: The Decision Log

To maintain architectural stability when customized nodes or new Agents (e.g., Architect Swarms) modify the Deep Pulse architecture, this living log tracks intentional limitations and rejected ideas. Future Agents **must** cross-reference this log before attempting heavy architectural refactors.

| Date | Category | Decision | Rationale |
|---|---|---|---|
| 2026-04 | Protocol Architecture | **Rejected `py-libp2p` native implementation.** | The Python port of Libp2p introduces too much library bloat natively, crashing minimal local deployments on 4-core ARM VMs. Decided to utilize a custom Tor-Aware `asyncio.start_server` SOCKS5 manual byte negotiation implementation instead. |
| 2026-04 | Anti-Bot Steering | **Rejected `CrawlerRunConfig` `magic_kwargs`.** | Crawl4AI `0.8.x` deprecated evasion parameters inside the crawler scope. Future agents must map `enable_stealth=True` natively inside `BrowserConfig`. |
| 2026-04 | Discovery Architecture | **Architect Swarm adopted.** | Abandoned static pre-definition libraries in favor of an active, self-discovering "Architect Swarm" capable of fetching changing API architectures (like NASA/USGS modernizations) to build 'Smart YAML' configurations on the fly. |
| 2026-04 | P2P Networking | **Peer Health Rotation established.** | Implemented native latency tracking for .onion peers. If latency > 1500ms, the node triggers a circuit rotation or PEX query to maintain Gossip stream integrity. |
| 2026-04 | Audit & Transparency | **Indelible Audit Log mandated.** | Every high-level query to the Base Ledger must be hashed and signed with Ed25519 to ensure non-repudiation and voluntary transparency in the Truth Economy. |
| 2026-04 | Orchestration | **LangGraph State Machine adopted.** | Moved DEC (Dynamic Error Control) Layer to a strict LangGraph state machine. Replaces loose manager logic with deterministic 'Error -> Recon -> Schema -> Gate' flow to prevent SLM wander. |
| 2026-04 | Personalization | **Navigator Profile defined.** | Created `profile.yaml` for Interests, Knowledge, and Capabilities mapping. Used for semantic salience ranking and task delegation logic. |
| 2026-04 | Schema Evolution | **Auto-repaired `https://energycommerce.house.gov/news/archive`.** | Architect Swarm detected drift and user approved the update via CLI gate. |
| 2026-04 | Schema Evolution | **Auto-repaired `https://polb.com/business/port-statistics/`.** | Architect Swarm detected drift and user approved the update via CLI gate. |
