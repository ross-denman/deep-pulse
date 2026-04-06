# Onboarding: Joining the Swarm

Welcome, Navigator. You are part of the decentralized "Truth Economy."

## Prerequisites
- **Python 3.12+**
- **Neo4j** (Optional, if running deep-ledger)
- **Ollama** or an LLM API key (OpenAI/Anthropic)

## Steps to Join
1. **Clone the Repo** and install dependencies.
2. **Init Identity**: `python3 src/pulse.py init`. This generates your Ed25519 keys.
3. **Configure .env**: Set your `LLM_PROVIDER`.
4. **Adaptive RAG**: We recommend running a tiny local model (e.g., Qwen2-0.5B) for Tier 0 processing to save costs.
5. **Start Scouting**: Choose a perimeter in `templates/perimeters/` and run `pulse scout run`.

## Linux / Headless Server Requirements
If you are running Deep Pulse on a headless server (like an Oracle Cloud VM), you must install the OS-level browser dependencies. Failure to do so will result in a `BrowserType.launch: Executable doesn't exist` error.

```bash
# Install system deps and Chromium
python3 src/scripts/setup_crawler.sh
```

## Reputation Tiers
- **Tier 0 (Lurker)**: 0-99 REP. Access to older, verified data.
- **Tier 1 (Scout)**: 100-499 REP. Can submit and verify claims.
- **Tier 2 (Master Auditor)**: 500+ REP. Can settle disputes and slash bad actors.
