# Deep Pulse: Coding & Protocol Conventions

This document tracks established engineering practices and API signatures to prevent future regression loops and simplify cross-swarm development.

## 1. Python Sub-Module Importing
- Deep Pulse CLI scripts (like `src/pulse.py` or `.scripts/preflight.py`) must always include a local root insertion for module discovery.
- **Rule**: Never assume the user exported `PYTHONPATH`. 
- **Implementation**:
  ```python
  import sys
  import os
  sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../'))
  ```

## 2. Crawl4AI Best Practices
- **Version Awareness**: We currently rely on the `0.8.x` branch structure.
- **Bot Evasion**: Do not pass `magic_kwargs` or `bypass_anti_bot` inside `CrawlerRunConfig`. These properties are deprecated or non-standard.
- **Standard**: The stealth components and TLS/SSL exception handlers must be natively declared in `BrowserConfig`.
  ```python
  browser_cfg = BrowserConfig(
      headless=True, 
      java_script_enabled=True, 
      enable_stealth=True, 
      ignore_https_errors=True,
      user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) ..."
  )
  ```

## 3. P2P Independence
- Never assume an internet connection or available Cloud API budget.
- The `src/core/config.py` runs a health check endpoint against the `LOCAL_DISTILL_URL`. Always design Scouts to attempt to route chunk ingestion to a local distillator (Tier 0) to defend the Cloud API budget (Tier 1).

## 4. Requirement Dependencies
- Do not place Python standard libraries (e.g., `asyncio`, `argparse`, `sqlite3`) inside `requirements.txt`.
- LibP2P wrappers currently throw wheel construction errors in strict Linux envs. Isolate experimental bridges from core requirements.
## 5. Anonymity & Investigative Privacy
- **Architecture**: Separate the Human (PII-free) from the Node (Ed25519 Pubkey).
- **Profile Secrecy**: The `navigator_profile.yaml` is LOCAL-ONLY. Only Interest CIDs are shared with the swarm.
- **REP-G (Weight)**: Performance-based reputation is earned by verifying pulses. Initial nodes (0 REP-G) are Sybil-restricted from consensus.
- **Subscription Manifest**: Interest broadcasts MUST use the `Deep Pulse Subscription Manifest v1.0` context.
