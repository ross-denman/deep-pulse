# 📡 Discovery Mesh: Curiosity Outpost
### *Autonomous Intelligence Scouting & Training Sandbox*

The **Discovery Mesh** (Deep Pulse) is the public edge of the Sovereign Auditor framework. It is designed to run on local hardware (Desktop clones, Pi Zero 2 W) to harvest intelligence, participate in mesh consensus, and build reputation through the **Onboarding Sandbox**.

## 🔑 Your Journey: From Provisional to Auditor

New nodes enter the mesh with **Provisional Status**. To protect the integrity of the Master Chronicle, you must first complete the **Auditor's Exam**.

1.  **Provisional Status**: Shadow-access to all local investigative tools (Neo4j, Briefings) but firewalled from global posting.
2.  **The Training Board**: Complete 10 archival verification tasks to earn your first **10 Grains** and **+1.0 Reputation**.
3.  **Promotion**: Automated promotion to **Auditor** unlocks the ability to "Sow" new inquiries and participate in global 2+1/3+1 triangulation.

## 🚀 Installation (Clean Slate)

### 1. Requirements
Ensure you have Python 3.10+ and the core dependencies installed:
```bash
pip install -r requirements.txt
```

### 2. Initialize Identity
Generate your Ed25519 Sovereign Identity. This is your "Seal" for all future discoveries.
```bash
python3 src/public/core/identity_generator.py
```

### 3. Check Status
Verify your current rank and reputation:
```bash
python3 src/public/auditor_cli.py status
```
*Expected Output: [PROVISIONAL] with 0.0 Reputation.*

## 💾 Hybrid Sovereignty: KùzuDB Edge Graph
To ensure maximum agility on low-resource hardware (Pi Zero 2 W), Discovery Mesh outposts use **KùzuDB** as their embedded knowledge graph.

- **Zero Zero Footprint**: Runs as a Python library with ~100MB RAM usage.
- **Cypher Compatible**: Uses the same query patterns as the Sovereign Notary's Neo4j Master Chronicle.
- **Portability**: The entire graph is stored in `harvest/kuzu_db/`, making your container fully portable.

## 🕵️ Scouting Operations

### 1. View Training Board
List the "Low-Gravity" archival tasks meant for training:
```bash
python3 src/public/auditor_cli.py inquiry --training
```

### 2. Submit a Training Discovery
Execute forensic labor on an archival pulse (e.g., verifying a Hormuz status) and submit it to earn Seed Grains:
```bash
python3 src/public/auditor_cli.py train <id> "<your_finding>"
```

### 3. Global Mesh Sync
Once promoted to **Auditor**, synchronize the latest settled truth from the network:
```bash
python3 src/public/auditor_cli.py sync
```

## 📁 Repository Structure
- **`src/public/auditor_cli.py`**: The primary Command Bridge for all outpost operations.
- **`src/public/core/`**: Reputation logic, Mesh Client, and Identity management.
- **`src/public/scouts/`**: Modular scanning templates for web and institutional portals.

---
**Standard**: MultiSignature2026
**Role**: Curiosity Outpost (Shell)
**Port**: 4110 (Bridge)
