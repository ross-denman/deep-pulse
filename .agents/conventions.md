# 🏴‍☠️ Soul Ledger — Global Conventions & Standards

> The high-level "Tribal Knowledge" governing the Sovereign Auditor Framework.

---

## 1. Project Philosophy (The Forensic-Agricultural Lexicon)
- **Convention**: We use "Forensic-Agricultural" terminology to describe our work.
- **Terminology**: 
    - **The Nexus**: The private processing hub (Master Outpost).
    - **The Shell**: The public Discovery Mesh (Public Outpost).
    - **Grains of Truth**: Validated data points.
    - **Harvesting**: The act of data collection.
    - **Settling the Record**: The final archival of a verified chronicle.

## 2. Repository Architecture & Subtrees
- **Convention**: `soul-ledger` is the **Master Vault**.
- **Convention**: Core components are managed as modular subdirectories:
    - `deep-ledger/`: The Sovereign Notary logic.
    - `deep-pulse/`: The Outpost logic (Nexus & Shell).
- **Convention**: Global documentation (root `docs/`) must maintain parity across all sub-projects.

## 3. Communication Standards
- **Convention**: Communication between `deep-pulse` (Public) and `deep-ledger` (Private) is strictly decoupled.
- **Convention**: Interaction occurs over local HTTP bridges:
    - **Port 4110**: Information exchanges and ledger queries.
    - **Port 9110**: Emergency pulses and high-priority alerts.

## 4. Security & Privacy
- **Convention**: Master identities (Ed25519) are stored in individual `.env` files within subdirectories.
- **Convention**: The root `.gitignore` must prevent any accidental leak of `.env` or `*.hex` identity files from sub-projects.
- **Convention**: "The Obsidian Pillar" (Oracle Cloud Instance) is the reference deployment for the Sovereign Notary.

## 5. Development Workflow
- **Convention**: All significant architectural shifts require a "Mental Lighthouse" update in `history.md`.
- **Convention**: Sprints are managed globally in `.agents/sprints/`.
- **Convention**: Code changes in sub-projects must be verified against the global reputation and consensus models defined in `deep-ledger`.

## 6. Reputation & Integrity
- **Convention**: We adhere to the **2+1 Triangulation Rule** for all chronicle settlements.
- **Convention**: Semantic Hallucinations result in immediate compute credit slashing.
## 7. The State-Orchestrated Economy
- **Issue**: System-generated inquiries leading to "Truth Inflation" and verifier reward dilution.
- **Solution**: Implemented a Sovereign Treasury and a Fixed Pool Settlement Engine (60/20/20).
- **Convention**: All inquiries must have grains escrowed from the Treasury before being sown.
- **Convention**: Use the **3+1 Rule** for speculative sources; standard sources follow **2+1 Triangulation**.
- **Convention**: Round down all grain splits; fractional "Dust" must be returned to the Treasury as a maintenance fee.
- **Date**: 2026-04-09
