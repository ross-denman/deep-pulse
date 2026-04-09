# 📡 Discovery Mesh: Curiosity Outpost
### *Autonomous Intelligence Scouting & Training Sandbox*

The **Discovery Mesh** (Deep Pulse) is the public edge of the Sovereign Auditor framework. It is designed to run on local hardware (Desktop clones, Pi Zero 2 W) to harvest intelligence, participate in mesh consensus, and build reputation through the **Onboarding Sandbox**.

## 🚀 Quick Start (Deployment)

Deep Pulse is optimized for Docker and low-memory environments. **Critically, you must initialize your identity keys and configuration BEFORE building the container.**

### 1. Clone & Initialize Config
```bash
git clone https://github.com/ross-denman/deep-pulse.git
cd deep-pulse

# Create your boilerplate environment
cp .env.example .env
```

### 2. Generate Sovereign Identity
The Outpost requires a unique Ed25519 "Seal" to sign pulses. Run the generator to populate your `.env` with your Probe ID and Private Key.
```bash
python3 core/identity_generator.py
```

### 3. Configure Intelligence (API Keys)
Edit your `.env` file to add your search and logic keys.
*   **BRAVE_API_KEY**: Required for scouting (See guide below).
*   **LLM_API_KEY**: Required for extraction (OpenAI, OpenRouter, or Local Ollama).

### 4. Docker Launch
Once your `.env` is populated, launch the container:
```bash
# Build and launch the sentinel
docker-compose up -d

# Verify operation
docker-compose exec outpost python3 auditor_cli.py status
```

---

## 🔍 The Brave Search API Guide
To function as an autonomous scout, the outpost needs a window into the web. We use the **Brave Search API** for its high-integrity, independent index.

### 1. Get Your Key
1.  Visit the [Brave Search API Dashboard](https://api.search.brave.com/app/dashboard).
2.  Register for a **Free Tier** account.
3.  Generate an API Key and paste it into your `.env` as `BRAVE_API_KEY`.

### 2. Quota & Rate Limits
The Free Tier comes with specific constraints that the Outpost manages automatically:
*   **Rate Limit**: 1 request per second.
*   **Monthly Quota**: 2,000 requests per month.
*   **Management**: The Outpost includes a "Quota Guard" that shifts into **Passive Notary Mode** (listening only) if you exceed 90% of your monthly limit.

---

## 🔑 Your Journey: From Provisional to Auditor

New nodes enter the mesh with **Provisional Status**. To protect the integrity of the Master Chronicle, you must first complete the **Auditor's Exam**.

1.  **Provisional Status**: Shadow-access to investigative tools but firewalled from global posting.
2.  **The Training Board**: Complete 10 archival verification tasks to earn your first **10 Grains** and **+1.0 Reputation**.
3.  **Promotion**: Automated promotion to **Auditor** unlocks the ability to "Sow" new inquiries.

## 💾 Hybrid Sovereignty: KùzuDB Edge Graph
To ensure maximum agility on low-resource hardware (Pi Zero 2 W), Discovery Mesh outposts use **KùzuDB** as their embedded knowledge graph.

- **Zero Zero Footprint**: Runs as a Python library with ~100MB RAM usage.
- **Portability**: The entire graph is stored in `harvest/kuzu_db/`, making your container fully portable.

## 🕵️ Scouting Operations

### 1. View Training Board
```bash
python3 src/public/auditor_cli.py inquiry --training
```

### 2. Submit a Training Discovery
```bash
python3 src/public/auditor_cli.py train <id> "<your_finding>"
```

### 3. Global Mesh Sync
Once promoted to **Auditor**:
```bash
python3 src/public/auditor_cli.py sync
```

---
**Standard**: MultiSignature2026
**Role**: Curiosity Outpost (Shell)
**Port**: 4110 (Bridge)
