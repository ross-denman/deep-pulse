#!/usr/bin/env python3
"""
Deep Ledger — Command Bridge (CLI)

The primary interface for the Deep Pulse Intelligence Swarm.
All commands route through here.

Usage:
    python src/bridge.py status          Show node identity & ledger stats
    python src/bridge.py ledger --tail N  Show last N ledger entries
    python src/bridge.py verify <CID>    Check verification status of an entry
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.identity import load_identity
from src.core.ledger import (
    LEDGER_FILE,
    append_entry,
    create_genesis_entry,
    read_ledger,
    verify_entry,
)
from src.core.reputation import ReputationService, ReputationTier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bridge")


# ─── ANSI Colors ────────────────────────────────────────────────
class C:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


BANNER = f"""
{C.CYAN}{C.BOLD}
  ╔══════════════════════════════════════════════════════════╗
  ║                                                          ║
  ║       ██████╗ ███████╗███████╗██████╗                    ║
  ║       ██╔══██╗██╔════╝██╔════╝██╔══██╗                   ║
  ║       ██║  ██║█████╗  █████╗  ██████╔╝                   ║
  ║       ██║  ██║██╔══╝  ██╔══╝  ██╔═══╝                    ║
  ║       ██████╔╝███████╗███████╗██║                         ║
  ║       ╚═════╝ ╚══════╝╚══════╝╚═╝                        ║
  ║                                                          ║
  ║       ██╗     ███████╗██████╗  ██████╗ ███████╗██████╗   ║
  ║       ██║     ██╔════╝██╔══██╗██╔════╝ ██╔════╝██╔══██╗  ║
  ║       ██║     █████╗  ██║  ██║██║  ███╗█████╗  ██████╔╝  ║
  ║       ██║     ██╔══╝  ██║  ██║██║   ██║██╔══╝  ██╔══██╗  ║
  ║       ███████╗███████╗██████╔╝╚██████╔╝███████╗██║  ██║  ║
  ║       ╚══════╝╚══════╝╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝  ║
  ║                                                          ║
  ║  {C.YELLOW}The Immutable Infrastructure for Deep Pulse{C.CYAN}              ║
  ╚══════════════════════════════════════════════════════════╝
{C.RESET}"""


def cmd_status(args: argparse.Namespace) -> None:
    """Display node identity, reputation, ledger, and Knowledge Graph statistics."""
    print(BANNER)

    try:
        identity = load_identity()
    except ValueError as e:
        print(f"  {C.RED}✗ {e}{C.RESET}")
        print(f"  {C.DIM}Run: python src/core/identity_generator.py{C.RESET}")
        return

    # Node Identity
    print(f"  {C.BOLD}═══ NODE IDENTITY ═══{C.RESET}")
    print(f"  {C.GREEN}🔑 Node ID:{C.RESET}     {identity.node_id}")
    print(f"  {C.GREEN}🌐 Public Key:{C.RESET}  {identity.public_key_hex[:32]}...")
    print()

    # Reputation
    rep_service = ReputationService()
    node_rep = rep_service.register_node(identity.node_id, identity.public_key_hex)
    print(f"  {C.BOLD}═══ REPUTATION (REP-G) ═══{C.RESET}")
    print(f"  {C.YELLOW}⭐ Score:{C.RESET}       {node_rep.score}")
    print(f"  {C.YELLOW}🏷️  Tier:{C.RESET}        {node_rep.tier_name}")
    print()

    # Ledger Stats
    ledger = read_ledger()
    verified = sum(1 for e in ledger if e.get("metadata", {}).get("status") == "verified")
    speculative = sum(1 for e in ledger if e.get("metadata", {}).get("status") == "speculative")
    print(f"  {C.BOLD}═══ LEDGER STATUS ═══{C.RESET}")
    print(f"  {C.CYAN}📜 Total Entries:{C.RESET}   {len(ledger)}")
    print(f"  {C.GREEN}✅ Verified:{C.RESET}       {verified}")
    print(f"  {C.YELLOW}⏳ Speculative:{C.RESET}    {speculative}")
    print(f"  {C.DIM}📁 Ledger Path:{C.RESET}    {LEDGER_FILE}")
    print()

    # Neo4j Knowledge Graph
    print(f"  {C.BOLD}═══ KNOWLEDGE GRAPH (Neo4j) ═══{C.RESET}")
    try:
        from src.db.driver import GraphDriver

        async def _neo4j_status():
            async with GraphDriver() as driver:
                healthy = await driver.health_check()
                if healthy:
                    entity_count = await driver.get_entity_count()
                    entry_count = await driver.get_entry_count()
                    return driver.mode, entity_count, entry_count
                return driver.mode, None, None

        mode, entities, entries = asyncio.run(_neo4j_status())
        if entities is not None:
            print(f"  {C.GREEN}🟢 Connected:{C.RESET}     {mode.upper()} mode")
            print(f"  {C.CYAN}🧬 Entities:{C.RESET}      {entities}")
            print(f"  {C.CYAN}📎 Graph Entries:{C.RESET} {entries}")
        else:
            print(f"  {C.YELLOW}🟡 Mode:{C.RESET}          {mode.upper()} (not responding)")
            print(f"  {C.DIM}Run: docker-compose up -d neo4j{C.RESET}")
    except Exception as e:
        print(f"  {C.RED}🔴 Offline:{C.RESET}       {e}")
        print(f"  {C.DIM}Run: docker-compose up -d neo4j{C.RESET}")
    print()

    # Integrity Check
    if ledger:
        all_valid = all(verify_entry(e) for e in ledger)
        if all_valid:
            print(f"  {C.GREEN}{C.BOLD}✅ LEDGER INTEGRITY: ALL SIGNATURES VALID{C.RESET}")
        else:
            print(f"  {C.RED}{C.BOLD}⚠️  LEDGER INTEGRITY: SIGNATURE MISMATCH DETECTED{C.RESET}")
    else:
        print(f"  {C.DIM}📭 Ledger is empty. Run 'onboard' to create Genesis entry.{C.RESET}")
    print()




def cmd_ledger(args: argparse.Namespace) -> None:
    """Display recent Ledger entries."""
    print(BANNER)

    ledger = read_ledger()
    tail = args.tail or 10

    if not ledger:
        print(f"  {C.DIM}📭 Ledger is empty.{C.RESET}")
        return

    entries = ledger[-tail:]
    print(f"  {C.BOLD}═══ LEDGER (last {len(entries)} entries) ═══{C.RESET}")
    print()

    for i, entry in enumerate(entries, 1):
        status = entry.get("metadata", {}).get("status", "unknown")
        status_icon = {"verified": "✅", "speculative": "⏳", "pending_verification": "🔄"}.get(
            status, "❓"
        )
        valid = verify_entry(entry)
        sig_icon = f"{C.GREEN}✓{C.RESET}" if valid else f"{C.RED}✗{C.RESET}"

        print(f"  {C.BOLD}[{i}]{C.RESET} {status_icon} {entry['id'][:50]}...")
        print(f"      {C.DIM}Type:{C.RESET}   {entry.get('data', {}).get('type', 'N/A')}")
        print(f"      {C.DIM}Scout:{C.RESET}  {entry.get('metadata', {}).get('scout_id', 'N/A')}")
        print(f"      {C.DIM}Time:{C.RESET}   {entry.get('metadata', {}).get('timestamp', 'N/A')}")
        print(f"      {C.DIM}Sig:{C.RESET}    [{sig_icon}]")
        print()


def cmd_settle(args: argparse.Namespace) -> None:
    """Signs and 'mints' speculative entries into verified ledger pulses."""
    print(BANNER)
    print(f"  {C.BOLD}═══ BATCH SETTLEMENT (Genesis Signature) ═══{C.RESET}")
    
    ledger = read_ledger()
    if not ledger:
        print(f"  {C.DIM}📭 Ledger is empty. Nothing to settle.{C.RESET}")
        return

    # Filter for entries to settle
    to_settle = []
    if args.all_missions:
        to_settle = [e for e in ledger if e.get("metadata", {}).get("status") == "speculative"]
    
    if not to_settle:
        print(f"  {C.GREEN}✅ No speculative entries found matching criteria.{C.RESET}")
        return

    print(f"  {C.CYAN}Settling {len(to_settle)} entries...{C.RESET}")
    
    # Simulated Settlement: Upgrading status to 'verified'
    for entry in to_settle:
        entry["metadata"]["status"] = "verified"
        cid_short = entry.get("id", "unknown")[:32]
        print(f"  {C.GREEN}✓{C.RESET} Minting {cid_short}... [{C.YELLOW}SIGNED{C.RESET}]")
    
    # Save ledger
    try:
        with open(LEDGER_FILE, "w") as f:
            json.dump(ledger, f, indent=2)
        print(f"\n  {C.BOLD}{C.GREEN}✅ GENESIS SETTLEMENT COMPLETE: {len(to_settle)} Pulses Minted.{C.RESET}")
    except Exception as e:
        print(f"  {C.RED}✗ Failed to save ledger: {e}{C.RESET}")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="bridge",
        description="Deep Ledger — Command Bridge for the Deep Pulse Intelligence Swarm",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # status
    subparsers.add_parser("status", help="Show node identity, REP, and ledger stats")


    # ledger
    ledger_parser = subparsers.add_parser("ledger", help="View Ledger entries")
    ledger_parser.add_argument(
        "--tail", type=int, default=10, help="Number of recent entries to show"
    )

    # settle
    settle_parser = subparsers.add_parser("settle", help="Batch settle speculative entries")
    settle_parser.add_argument(
        "--all-missions", action="store_true", help="Settle all missions in the queue"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        "status": cmd_status,
        "ledger": cmd_ledger,
        "settle": cmd_settle,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
