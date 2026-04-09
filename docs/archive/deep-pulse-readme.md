# 📡 Deep Pulse: Curiosity Outpost
### *Autonomous Intelligence Scouting for the Discovery Mesh*

**Deep Pulse** is the scouting layer of the Sovereign Auditor framework. It is designed to run on low-resource hardware (Pi, VPS, or local containers) to autonomously probe institutional portals and harvest high-resolution intelligence.

## 🔑 Core Principles

| Principle | Description |
| :--- | :--- |
| **Sovereign Identity** | You are your own root of trust. Your Ed25519 **Seal** verifies every discovery. |
| **Curiosity Probes** | Automated probes that seek out structural divergences and institutional shifts. |
| **Discovery Mesh** | A distributed gossip network for synchronizing truth pulses across outposts. |
| **Grounding Check** | Every discovery is audited against Primary Engine anchors before settlement. |

## 🚀 Quick Start (Deployment)

Deep Pulse is optimized for Docker and low-memory environments.

```bash
# 1. Clone the Outpost
git clone https://github.com/ross-denman/deep-pulse.git
cd deep-pulse

# 2. Build the Environment
docker-compose up -d

# 3. Generate Outpost Identity
docker-compose exec outpost python3 src/core/identity_generator.py

# 4. Join the Mesh
docker-compose exec outpost python3 src/bridge.py onboard
```

## 🕵️ Scouting Operations

Once your outpost is live, you can deploy **Curiosity Probes** or manually submit intelligence for settlement.

### Submit a Truth Pulse
```bash
python src/bridge.py submit --content "Your discovery payload..."
```

### Mesh Synchronization
```bash
# Sync missing chronicle entries from peers
python src/bridge.py sync --mesh

# Check mesh connectivity
python src/bridge.py p2p --status
```

### View Local Chronicle
```bash
python src/bridge.py chronicle --tail 10
```

## 📁 Outpost Structure

```
deep-pulse/
├── src/
│   ├── agents/           # Curiosity Probes (The Scrapers)
│   ├── core/             # Outpost Protocol & Identity
│   ├── private/          # Local Bridge API & Node-specific logic
│   └── bridge.py         # Outpost Management CLI
├── .env.example          # Template for Outpost configuration
└── docker-compose.yml    # Outpost Infrastructure
```

## 🔐 Data Standard (v1.2)
All submissions are notarized using the **MultiSignature2026** standard, ensuring your identity is cryptographically tied to the truth you help settle.

---
**Status**: ACTIVE
**Role**: Curiosity Outpost
**Mesh Port**: 4110
