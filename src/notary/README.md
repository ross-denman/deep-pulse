# 📜 The Sovereign Notary
### *Authoritative State & Settlement Core*

The **Sovereign Notary** (Deep Ledger) is the private core of the Soul Ledger framework. It acts as the "Central Brain" of the mesh, managing the truth marketplace, the reputation ledger ($REP-G), and the immutable archival of settled Grains.

## 🔑 Core Logic Foundations

- **The Epistemic Firewall**: Implements dynamic status gates. Nodes with **Provisional Status** are restricted to the sandbox until they reach the 1.0 Reputation threshold.
- **The State Machine**: Manages the lifecycle of inquiries from "Sown" to "Settled" via 2+1 and 3+1 Multi-Sig consensus.
- **The Reputation Ledger**: Tracks the flow of Grains, handles daily yield, and enforces "Forgiveness Decay" for negative reputation recovery.

## 🚀 Engine Installation & Use

### 1. Requirements
The Notary requires a Flask environment and access to the `harvest/` directory:
```bash
pip install -r requirements.txt
```

### 2. Start the State Orchestrator
To activate the marketplace and the training sandbox, launch the server:
```bash
export PYTHONPATH=$PYTHONPATH:.
python3 src/notary/api/server.py
```
*The server defaults to port 4110.*

### 3. Automated Seeding (Dust Collector)
To seed the training board with archival data (Sprint 01-14 historical truths), run the collector:
```bash
python3 src/notary/core/dust_collector.py
```

## 📂 Core Structure
- **`src/notary/api/server.py`**: The primary API gateway and firewall hub.
- **`src/notary/core/state_machine.py`**: SQLite-backed orchestrator for inquiries and verifications.
- **`src/notary/core/reputation_ledger.py`**: Economic logic for payouts, splits (60/20/20), and dust collection.
- **`src/notary/core/dust_collector.py`**: Hybrid script for archival task generation.

---
**Status**: AUTHORITATIVE
**Standard**: MultiSignature2026
**Role**: Master State (The Obsidian Pillar)
