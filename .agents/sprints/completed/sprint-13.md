# Sprint 13: The Incentive Handshake
**Status: Completed**

## Overview
This sprint focused on hardening the **Sovereign Notary** architecture by transitioning the repository to a modular, root-level structure and implementing the **Incentive Handshake** protocol. This refactor resolves the "Conceptual Hole" in the state machine, ensuring every discovery is backed by signed intent and mesh consensus (2+1 Settlement).

## Implementation
### Tasks
- `[x]` **Modular Refactor**: Migrated `/src` to the root and established tripartite isolation (`notary/`, `public/`, `private/`).
- `[x]` **Cryptographic Handshake**: Implemented `ClaimHandshake` and `ProofOfDiscovery` persistent contracts.
- `[x]` **Liveness Metabolism**: Introduced `liveness_score` to track Auditor reliability and gatekeep high-gravity bounties.
- `[x]` **Auditor Rebranding**: Rebranded the Command Bridge to `auditor_cli.py` and decoupled it from the Notary domain.
- `[x]` **Gossip Pool**: Established `verification_pool.jsonld` for mesh-wide state awareness.
- `[x]` **Documentation Recovery**: Restored legacy roadmap and utility scripts to the root for future reference.

### Verifications and testing
- `[x]` Verified import isolation: `src/public` no longer has direct dependencies on the Notary service.
- `[x]` Pydantic validation: All handshake contracts pass serialization and signing unit tests.
- `[x]` Path Stability: Verified that `load_identity` correctly resolves `.env` from the project root.

**Upon Completion**
- `[x]` Update project README.md with implementations
- `[x]` Update roadmap.md with "Completed" status
- `[x]` Add summarized debrief of this sprint to the history.md
- `[x]` Filed to .agents/sprints/completed
