# Sprint16: The Onboarding & Provisional Path
**Status: Completed**

## Overview
This sprint focuses on establishing a "Low-Stakes Sandbox" for new nodes (Desktop clones and Pi 0w2 sentinels). The core objective is to allow fresh identities to earn "Seed Grains" and build reputation through archival verification tasks without risking the integrity of the high-gravity Master Chronicle. We are implementing a "Provisional" status system, a dedicated training pipeline, and automated promotion/demotion logic.

## Implementation
### Tasks

#### 1. The Sandbox Infrastructure (The Firewall)
- [x] **Initialize Training Endpoint**: Create `POST /api/v1/training/submit` in `server.py`. This endpoint must be isolated from the global verification pool.
- [x] **Firewall Middleware**: Implement a decorator to block `Provisional` users from global `POST /inquiries/complete` actions, redirecting them to the training path with a "Level Up Required" alert.
- [x] **Server-Side Key Validation**: Implement logic to verify training submissions against a server-side answer key.

#### 2. The Dust Collector (Archival Seeding)
- [x] **Build `dust_collector.py`**: Create the script in `src/notary/core/` to pull snippets from Sprint 01-14 historical data (Ghalibaf, Hormuz signals, etc.).
- [x] **Forensic Humility Logic**: Code the Collector to reward "Inconclusive" findings for ambiguous tasks, penalizing confident guesses where evidence is lacking.
- [x] **Archival Training Board**: Implement the "Training Inquiries" filter on the Request Board.

#### 3. The Status Metabolism (Dynamics)
- [x] **Automated Promotion**: Implement logic in `reputation_ledger.py` to trigger `Status: Auditor` when a node reaches **+1.0 Reputation**. 
- [x] **Demotion & The Floor**: Implement a demotion trigger that drops an Auditor back to `Provisional` if reputation hits **0.0**.
- [x] **Forgiveness Decay**: Implement a "Negative Decay" where reputations below 0.0 slowly drift back toward 0.0 over time (e.g., +0.01/day) to allow recovery from hardware outages or liveness hits.

#### 4. Auditor CLI Refinements (UX)
- [x] **Visual Rank Badging**: Update `auditor_cli.py` to display status with ANSI color coding:
    - `[PROVISIONAL]` (Dim Grey/Cyan)
    - `[AUDITOR]` (Bold Amber)
    - `[SKEPTIC]` (Flickering Red)
- [x] **Training Filter**: Add a `--training` flag to the `list-inquiries` command to filter the board for low-gravity tasks.

### Verifications and testing
- [ ] Verify that a `Provisional` node cannot POST to the global ledger.
- [ ] Test that a `Provisional` node earns fractional grains and reputation via the Training API.
- [ ] Verify the "Humility" penalty by submitting a confident guess to an ambiguous training task.
- [ ] Confirm "Auditor" promotion status updates the CLI display and unlocks global endpoints.

---

**Upon Completion**
- Update project `README.md` with implementations
- Update `deep-ledger-roadmap.md` accordingly
- **Add a summarized debrief of this sprint to the history.md**
- Update this file to **Status: Completed** and file to `.agents/sprints/completed`
