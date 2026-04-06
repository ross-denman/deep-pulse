#!/usr/bin/env python3
"""
Deep Pulse — CLI Bridge (Main Entry Point)

The primary interface for the Deep Pulse node.
Commands for identity management, scouting, swarm status, and reporting.
"""

import argparse
import asyncio
import logging
import os
import sys
import json
from typing import Dict, Any

# Ensure project root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.identity import IdentityManager
from src.core.config import ConfigManager
from src.core.economy import TruthEconomyManager
from src.core.memory import EpisodicMemory
from src.swarm.peer import PeerManager
from src.reporters.templates.brief_reporter import BriefReporter
from src.scouts.templates.web_scout import WebScout

class C:
    """Terminal colors."""
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    RESET = '\033[0m'

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("deep-pulse")

class PulseCLI:
    """The Command Bridge for a Deep Pulse node."""

    def __init__(self):
        self.config = ConfigManager()
        self.identity = IdentityManager()
        node_id = self.identity.load_identity() or "Uninitialized"
        self.economy = TruthEconomyManager(node_id)
        self.memory = EpisodicMemory()
        self.peers = PeerManager(node_id)
        
    def banner(self):
        """Displays the Pulse ASCII banner."""
        print("""
   ╔══════════════════════════════════════════════════════════╗
   ║                                                          ║
   ║       ██████╗ ██╗   ██╗██╗     ███████╗███████╗          ║
   ║       ██╔══██╗██║   ██║██║     ██╔════╝██╔════╝          ║
   ║       ██████╔╝██║   ██║██║     ███████╗█████╗            ║
   ║       ██╔═══╝ ██║   ██║██║     ╚════██║██╔══╝            ║
   ║       ██║     ╚██████╔╝███████╗███████║███████╗          ║
   ║       ╚═╝      ╚═════╝ ╚══════╝╚══════╝╚══════╝          ║
   ║                                                          ║
   ║  The P2P Intelligence Swarm for the Deep Pulse           ║
   ╚══════════════════════════════════════════════════════════╝
        """)

    async def init(self, silent=False):
        """Initializes the node: identity gen."""
        if not silent:
            self.banner()
            logger.info("Initializing Deep Pulse node...")
            
        node_id = self.identity.load_identity()
        if node_id:
            if not silent:
                logger.info(f"Node already initialized: {node_id}")
        else:
            node_id = self.identity.generate_identity()
            if not silent:
                logger.info(f"Generated new identity: {node_id}")
            
        if not silent:
            print(f"\n✅ Node Identity Set: {node_id}")
        return node_id

    def check_environment(self):
        """Pre-flight check for dependencies and settings (Sprint 09)."""
        import sys
        import os
        
        passed = True
        print(f"  {C.BOLD}═══ PRE-FLIGHT CHECK ═══{C.RESET}")
        
        # 1. Virtual Environment
        is_venv = hasattr(sys, 'real_prefix') or (sys.base_prefix != sys.prefix)
        if not is_venv:
            print(f"  [{C.RED}FAIL{C.RESET}] Not running in a virtual environment (.venv recommended).")
            passed = False
        else:
            print(f"  [{C.GREEN}PASS{C.RESET}] Virtual environment detected.")
            
        # 2. Dependencies
        try:
            import httpx
            # Crawl4AI might be tricky on some installs
            import crawl4ai
            print(f"  [{C.GREEN}PASS{C.RESET}] Core dependencies (crawl4ai, httpx) verified.")
        except ImportError as e:
            print(f"  [{C.RED}FAIL{C.RESET}] Missing dependency: {e.name}. Run 'pip install -r requirements.txt'")
            passed = False
            
        # 3. Identity Key
        if os.path.exists("identity.key"):
            print(f"  [{C.GREEN}PASS{C.RESET}] Ed25519 identity key verified.")
        else:
            # We don't fail here, onboard creates one, but scouts need it for signing
            print(f"  [{C.YELLOW}WARN{C.RESET}] No identity.key found. RUN: python3 src/pulse.py onboard")
            
        print()
        return passed

    async def onboard(self):
        """Run the Socratic onboarding — interactive perimeter definition."""
        self.check_environment()
        self.banner()
        print(f"  {C.BOLD}═══ SOCRATIC ONBOARDING ═══{C.RESET}")
        print(f"  {C.CYAN}Welcome, Navigator. Let's define your intelligence mission.{C.RESET}")
        print()

        # 1. Ensure identity
        node_id = await self.init(silent=True)

        # 2. Socratic Interview
        print(f"  {C.YELLOW}Q1: What is the unique ID for this perimeter? (e.g., indiana_water){C.RESET}")
        p_id = input("  > ").strip().lower().replace(" ", "_") or "custom_perimeter"

        print(f"\n  {C.YELLOW}Q2: What is the human-readable name? (e.g., Indiana Water Rights){C.RESET}")
        p_name = input("  > ").strip() or "Custom Intelligence Perimeter"

        print(f"\n  {C.YELLOW}Q3: Enter target URLs/Portals (comma-separated):{C.RESET}")
        p_targets = [t.strip() for t in input("  > ").split(",") if t.strip()]

        print(f"\n  {C.YELLOW}Q4: Enter search keywords (comma-separated):{C.RESET}")
        p_keywords = [k.strip() for k in input("  > ").split(",") if k.strip()]

        print(f"\n  {C.YELLOW}Q5: Compute Budget in USD? (default: 2.00){C.RESET}")
        p_budget = input("  > ").strip() or "2.00"

        # Phase 0: Reconnaissance (Broad Scan)
        if not p_targets:
            print(f"\n  {C.CYAN}No targets provided. Initiating Phase 0: Reconnaissance (Broad Scan)...{C.RESET}")
            from src.core.discovery import BraveDiscovery
            brave = BraveDiscovery()
            query = " ".join(p_keywords) if p_keywords else p_name
            discovered_urls = await brave.search(query, count=5)
            if discovered_urls:
                print(f"  {C.GREEN}Found {len(discovered_urls)} Genesis Points!{C.RESET}")
                p_targets = discovered_urls
            else:
                print(f"  {C.RED}Broad Scan failed to find targets. Proceeding with empty target list.{C.RESET}")

        # 3. Generate YAML
        import yaml
        perimeter_data = {
            "id": p_id,
            "name": p_name,
            "description": f"Intelligence perimeter for {p_name} defined via Socratic interview.",
            "keywords": p_keywords,
            "targets": [{"url": t, "type": "portal"} for t in p_targets],
            "recursive_depth": 3,
            "compute_budget": float(p_budget),
            "adaptive_rag": True
        }

        os.makedirs("templates/perimeters", exist_ok=True)
        yaml_path = f"templates/perimeters/{p_id}.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(perimeter_data, f, sort_keys=False)

        print(f"\n  {C.GREEN}✅ Intelligence Perimeter Defined: {yaml_path}{C.RESET}")
        print(f"  {C.DIM}Node ID:{C.RESET} {node_id}")
        print()
        print(f"  {C.CYAN}Mission active. Run the following to deploy your first scout:{C.RESET}")
        print(f"  python3 src/pulse.py scout run --template web --config {yaml_path}")
        print()

    async def scout_run(self, template: str, config_path: str):
        """Launches a scout."""
        self.check_environment()
        import yaml
        if not os.path.exists(config_path):
            logger.error(f"Config file not found: {config_path}")
            return

        with open(config_path, "r") as f:
            p_config = yaml.safe_load(f)

        p_id = p_config.get("id", "unknown")
        depth = p_config.get("recursive_depth", 3)
        
        self.banner()
        print(f"  {C.BOLD}═══ MISSION DEPLOYMENT ═══{C.RESET}")
        print(f"  {C.CYAN}Perimeter:{C.RESET}  {p_config.get('name', p_id)}")
        print(f"  {C.CYAN}Template:{C.RESET}   {template}")
        print(f"  {C.CYAN}Depth:{C.RESET}      {depth}")
        print()

        # Initialize Scout
        if template == "web":
            from src.scouts.templates.web_scout import WebScout
            scout = WebScout(p_id, self.config, self.economy, self.memory, recursive_depth=depth)
        elif template == "local":
            from src.scouts.templates.local_scout import LocalScout
            os.makedirs("data/local_ingest", exist_ok=True)
            scout = LocalScout(p_id, self.config, self.economy, self.memory, recursive_depth=depth)
        else:
            logger.error(f"Template {template} not yet implemented.")
            return

        # Run for each target
        targets = p_config.get("targets", [])
        keywords = p_config.get("keywords", [])
        
        for target in targets:
            url = target.get("url")
            if not url:
                continue
            
            logger.info(f"Targeting: {url}")
            params = target.copy()
            params["keywords"] = keywords
            result = await scout.run(params)
            if result:
                print(f"\n  {C.GREEN}🔍 Intelligence Found:{C.RESET}")
                print(f"  {result['data']}")
                print(f"  {C.CYAN}✅ Signed & Logged. CID:{C.RESET} {result.get('id', 'TBD')}")
                print()
            
        # 4. Debrief Phase (Heuristic Feedback Loop & Truth Synthesis)
        from src.core.analyst import LedgerAnalyst
        analyst = LedgerAnalyst()
        
        pulses = scout.success_data
        truth_insights = analyst.synthesize_truth(pulses, keywords)
        
        # 5. Outcome Analysis (Signal in the Silence)
        outcome_insights = analyst.evaluate_mission_outcome(p_id, pulses, scout.stats)
        truth_insights.extend(outcome_insights)
        
        if truth_insights:
            print(f"\n  {C.YELLOW}⚖️  SOURCES OF TRUTH DETECTED:{C.RESET}")
            for insight in truth_insights:
                status_color = C.GREEN if insight["status"] == "CONFIRMED" else C.YELLOW
                print(f"  [{status_color}{insight['status']}{C.RESET}] {insight['claim_keyword']} -> {insight['source']}")
                evidence = insight.get('evidence_fragment', 'N/A')
                print(f"  {C.ITALIC}Evidence: {evidence[:150]}...{C.RESET}")
        
        summary = scout.generate_summary(p_id)
        summary["truth_insights"] = truth_insights
        os.makedirs("data/history", exist_ok=True)
        summary_path = f"data/history/{p_id}_summary.json"
        
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
            
        logger.info(f"Mission {p_id} summary saved to {summary_path}")
        
        # Trigger Managing Agent Debrief
        from src.core.manager import AgentManager
        orchestrator = AgentManager()
        orchestrator.debrief_scout(p_id, summary, session_cost=scout.session_cost)

    async def swarm_status(self):
        """Displays swarm health."""
        self.banner()
        self.peers.discover_peers()
        status = self.peers.get_status()
        rep_g = self.economy.rep_g
        can_vote = self.economy.can_influence_consensus()
        
        print(f"\n🌐 Swarm Status:")
        print(f"- Node ID:         {os.getenv('NODE_ID')}")
        print(f"- Connected Peers: {status['active_count']}")
        print(f"- Bootstrapped:    {status['bootstrapped']}")
        print(f"- REP-G (Weight):  {C.GREEN if rep_g > 0 else C.YELLOW}{rep_g}{C.RESET}")
        print(f"- Consensus Power: {'Authorized' if can_vote else 'None (Sybil Restricted)'}")
        
        if not can_vote:
            print(f"\n{C.DIM}Note: New nodes start with zero REP-G and must verify pulses to earn weight.{C.RESET}")

    async def brief(self):
        """Generates the Sovereign Brief."""
        # Ledger bridge client would be passed here
        reporter = BriefReporter(None)
        await reporter.generate_report({"period": "daily"})

    async def broadcast_interests(self):
        """Broadcasts sector interests from the Navigator Profile to the swarm."""
        from src.swarm.gossip import PulseGossip
        import uuid
        
        self.banner()
        profile = self.config.load_navigator_profile()
        sectors = [s['sector'] if isinstance(s, dict) else s for s in profile.get('gossip_subscriptions', [])]
        
        if not sectors:
            logger.warning("No interests defined in templates/navigator_profile.yaml")
            return
            
        interest_cid = f"interest-{uuid.uuid4().hex[:8]}"
        gossip = PulseGossip()
        
        # Discover peers to broadcast to
        self.peers.discover_peers()
        peers = [p['address'] for p in self.peers.peers.values() if p.get('status') == 'active']
        
        if not peers:
            logger.warning("No active peers found to broadcast interests.")
            return

        print(f"  {C.CYAN}Broadcasting Subscription Manifest ({interest_cid})...{C.RESET}")
        print(f"  {C.CYAN}Sectors:{C.RESET} {', '.join(sectors)}")
        
        await gossip.broadcast_interests(peers, interest_cid, sectors)
        print(f"\n  {C.GREEN}✅ Interest CID Published. The swarm will now prioritize related pulses.{C.RESET}")

def main():
    parser = argparse.ArgumentParser(description="Deep Pulse Node Interface")
    subparsers = parser.add_subparsers(dest="command")

    # Command: init
    subparsers.add_parser("init", help="Initialize node identity")

    # Command: onboard
    subparsers.add_parser("onboard", help="Run interactive Socratic onboarding")

    # Command: scout run
    scout_parser = subparsers.add_parser("scout", help="Autonomous researcher controls")
    scout_sub = scout_parser.add_subparsers(dest="subcommand")
    scout_run = scout_sub.add_parser("run", help="Run a scout template")
    scout_run.add_argument("--template", required=True, choices=["web", "rss", "local"], help="Template to use")
    scout_run.add_argument("--config", required=True, help="Path to perimeter config YAML")

    # Command: swarm
    subparsers.add_parser("status", help="Show swarm health and connected peers")
    
    # Command: broadcast-interests
    subparsers.add_parser("broadcast-interests", help="Broadcast your Subscription Manifest to the swarm")

    # Command: brief
    subparsers.add_parser("brief", help="Generate your Sovereign Brief report")

    args = parser.parse_argument_tree() if hasattr(parser, 'parse_argument_tree') else parser.parse_args()
    
    cli = PulseCLI()

    if args.command == "init":
        asyncio.run(cli.init())
    elif args.command == "onboard":
        asyncio.run(cli.onboard())
    elif args.command == "scout" and args.subcommand == "run":
        asyncio.run(cli.scout_run(args.template, args.config))
    elif args.command == "status":
        asyncio.run(cli.swarm_status())
    elif args.command == "broadcast-interests":
        asyncio.run(cli.broadcast_interests())
    elif args.command == "brief":
        asyncio.run(cli.brief())
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
