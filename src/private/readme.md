# 🏛️ The Nexus: Private Processing Hub
### *Master Outpost for the Sovereign Notary*

**The Nexus** is the primary processing hub and physical "Home" of the **Sovereign Notary**. Unlike a standard **Probe**, the Nexus holds the authority to sign the **Public Chronicle** and manage the global **Master Outpost Queue**.

## 🏗️ Core Components

| Component | Description |
| :--- | :--- |
| `bridge_server.py` | The Sovereign Gateway. Handles P2P discovery, Gated Ingestion, and Hash Puzzle PoW for anonymous drops. |
| `daemon.py` | The Autonomous Hunt. Orchestrates the `HuntController` to process queued seeds based on search quotas. |
| `master_queue.py` | SQLite persistence for Investigative Seeds (Grains) and Inquiries. |
| `onion_gateway.py` | The Anonymous Bridge. Polls .onion RSS feeds via Tor to ingest deep-web intelligence. |
| `briefing_engine.py` | Intelligence Synthesis. Converts JSON pulses into human-readable Markdown Narrative Briefs. |

## 🛠️ Developer Operations (Manual Use)

### 1. Starting the Notary Bridge
The Bridge Server must be active to receive pulses from the mesh and process anonymous drops.
```bash
# From deep-pulse/ directory
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
python3 src/private/bridge_server.py
```
*Port: `4110` (includes SocketIO for real-time Anomaly Dashboard updates)*

### 2. Running the Nexus Daemon
The Daemon automates the investigative pipeline, scanning the `MasterOutpostQueue` and launching `WebScouts` for high-gravity targets.
```bash
python3 src/private/daemon.py
```
*Note: The Daemon includes a **Quota Guard** that shifts into "Passive Notary" mode when search API limits exceed 90%.*

### 3. Manually Injecting Seeds
You can manually enqueue new investigative targets into the `MasterOutpostQueue` using the `MasterOutpostQueue` class.
```python
from private.master_queue import MasterOutpostQueue
queue = MasterOutpostQueue()
queue.enqueue_grain(
    grain_id="id_123",
    title="Target Investigation",
    payload={"url": "https://example.gov"},
    gravity=8.5
)
```

## 🔌 Wiring to the Notary (Architectural Overview)

The Nexus "Wires" to the Sovereign Notary persona by implementing the **Authoritative State** logic defined in `src/public/core/`.

### Identity & Authority
- **Load Identity**: The Nexus loads the Ed25519 **Master Seed** from the `.env` file via `src.public.core.identity.load_identity()`.
- **Chronicle Signing**: Only the Nexus (and authorized Anchor Outposts) can perform `add_signature()` with a weight contributing to the `verified` status.

### The Epistemic Firewall
The `bridge_server.py` enforces the **Epistemic Firewall** through:
- **Hash Puzzle Verification**: Mandatory PoW for all anonymous pulse submissions.
- **Consensus Weighting**: Primary (.gov/.edu) sources receive a **1.5x multiplier**, while ephemeral social sources are gated by higher quorum requirements.
- **Conflict Handling**: Detects and notarizes `ConflictEvent` entries when high-signal anchors are challenged by speculative noise.

### Directory Structure
- `src/private/`: Sensitive, hub-only orchestration logic.
- `src/public/core/`: Shared mechanisms (Crypto, Chronicle, Reputation) used by both Nexus and Probes.
- `harvest/`: Local persistent state (Ledger, Queue, Discovery Vault).

---
**Status**: ACTIVE
**Role**: Master Hub
**Authority**: Sovereign Notary
