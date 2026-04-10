"""
The Chronicle - Command Bridge (Lightweight Dispatcher)
Phase 4 Refactor: Minimalist CLI Router
"""

import argparse
import asyncio
import json
import logging
import sys
import subprocess
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Lightweight imports for startup speed
from core.identity import load_identity
from core.chronicle import read_ledger
from core.reputation import ReputationService
from core.network import MeshClient
from storage.vault import DiscoveryVault

logging.basicConfig(level=logging.WARNING)

class C:
    HEADER, BLUE, CYAN, GREEN, YELLOW, RED, BOLD, DIM, RESET = (
        "\033[95m", "\033[94m", "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[1m", "\033[2m", "\033[0m"
    )

BANNER = f"{C.CYAN}{C.BOLD}=== The Chronicle: Auditor CLI ==={C.RESET}"

class Bridge:
    def __init__(self):
        self.client = MeshClient() # MeshClient is lightweight (requests wrapper)
        self._identity = None
        self._vault = None
        self._rep_service = None
        self._inquiry = None
        self._consensus = None
        self._archive = None
        self._laboratory = None

    @property
    def identity(self):
        if self._identity is None:
            self._identity = load_identity()
        return self._identity

    @property
    def vault(self):
        if self._vault is None:
            self._vault = DiscoveryVault(PROJECT_ROOT / "harvest" / "discovery_vault.json")
        return self._vault

    @property
    def rep_service(self):
        if self._rep_service is None:
            self._rep_service = ReputationService()
            self._rep_service.refresh_if_dirty(read_ledger())
        return self._rep_service

    @property
    def inquiry(self):
        if self._inquiry is None:
            from controllers.inquiry import InquiryController
            self._inquiry = InquiryController(self.client, self.identity, self.vault)
        return self._inquiry

    @property
    def consensus(self):
        if self._consensus is None:
            from controllers.consensus import ConsensusController
            self._consensus = ConsensusController(self.client, self.identity, self.rep_service)
        return self._consensus

    @property
    def archive(self):
        if self._archive is None:
            from controllers.archive import ArchiveController
            self._archive = ArchiveController(self.vault)
        return self._archive

    @property
    def laboratory(self):
        if self._laboratory is None:
            from controllers.laboratory import LaboratoryController
            self._laboratory = LaboratoryController()
        return self._laboratory

    def cmd_status(self, args):
        print(BANNER)
        rep = self.rep_service.get_outpost(self.identity.outpost_id)
        mesh = self.inquiry.get_mesh_state()
        valid, verified, total = self.consensus.audit_system_integrity()
        
        from core.reputation import ReputationTier
        
        # Sprint 16 Badge Logic
        if rep is None:
            badge = f"{C.CYAN}{C.DIM}[PROVISIONAL]{C.RESET}"
            score = 0.0
            grains = 0
        else:
            status_label = f"[{rep.tier.name}]"
            score = rep.score
            grains = rep.grain_balance
            if rep.tier.name == "UNVERIFIED":
                badge = f"{C.CYAN}{C.DIM}{status_label}{C.RESET}"
            elif rep.tier.name == "SCOUT":
                badge = f"{C.YELLOW}{status_label}{C.RESET}"
            elif rep.tier.name == "AUDITOR":
                badge = f"{C.YELLOW}{C.BOLD}{status_label}{C.RESET}"
            elif rep.tier.name == "SOVEREIGN_NOTARY":
                badge = f"{C.HEADER}{C.BOLD}{status_label}{C.RESET}"
            else:
                badge = status_label

            if rep.score < 0.5: # Near demotion or just started
                 badge = f"{C.RED}{C.BOLD}[SKEPTIC]{C.RESET} {badge}"

        print(f"  {C.YELLOW}Probe ID:{C.RESET}    {self.identity.outpost_id}")
        print(f"  {C.YELLOW}Status:{C.RESET}      {badge}")
        print(f"  {C.YELLOW}Reputation:{C.RESET}  {score}")
        print(f"  {C.YELLOW}Grains:{C.RESET}      {grains}")
        print(f"  {C.YELLOW}Chronicle:{C.RESET}   {total} entries ({C.GREEN if valid else C.RED}{verified} verified{C.RESET})")
        print(f"  {C.YELLOW}Mesh Peers:{C.RESET}  {len(mesh['peers'])}")
        print()

    def cmd_inquiry(self, args):
        if args.training:
            print(f"{C.HEADER}Listing Sandbox Training Inquiries...{C.RESET}")
            try:
                import requests
                resp = requests.get(f"{self.client.base_url}/api/v1/training")
                if resp.status_code == 200:
                    inqs = resp.json().get("tasks", [])
                    for i in inqs:
                         print(f"  [{i['id'][:8]}] {i['title']} - {C.CYAN}SANDBOX{C.RESET}")
                return
            except Exception as e:
                print(f"{C.RED}Failed to fetch training board: {e}{C.RESET}")
                return

        print(f"{C.CYAN}Listing active Sovereignty Inquiries...{C.RESET}")
        inqs = asyncio.run(self.inquiry.get_active_inquiries())
        for i in inqs:
            print(f"  [{i['id'][:8]}] {i['title']} - {C.YELLOW}{i['status']}{C.RESET}")

    def cmd_claim(self, args):
        res = self.inquiry.claim_inquiry(args.id)
        if res: print(f"{C.GREEN}✓{C.RESET} Inquiry {args.id} claimed and vaulted.")

    def cmd_submit(self, args):
        # Example: bridge submit inq_123 '{"data": "val"}' source.com
        payload = json.loads(args.payload)
        res = self.inquiry.submit_evidence(args.id, payload, args.source)
        if res: print(f"{C.GREEN}[OK] Pulse {res.get('id', 'unknown')} submitted.{C.RESET}")

    def cmd_train(self, args):
        """Isolated training submission for Seed Grains and Reputation."""
        print(f"{C.CYAN}Submitting Training Discovery for {args.id}...{C.RESET}")
        try:
            import requests
            payload = {
                "outpost_id": self.identity.outpost_id,
                "inquiry_id": args.id,
                "discovery": args.discovery
            }
            resp = requests.post(f"{self.client.base_url}/api/v1/training/submit", json=payload)
            data = resp.json()
            if resp.status_code == 200:
                print(f"{C.GREEN}[OK] {data['message']}{C.RESET}")
                print(f"  New Reputation: {data['current_rep']}")
            else:
                # Handle error responses which might be dict or string
                msg = data.get("message", data) if isinstance(data, dict) else data
                print(f"{C.RED}[ERR] {msg}{C.RESET}")
                if isinstance(data, dict) and "hint" in data:
                    print(f"  {C.DIM}Hint: {data['hint']}{C.RESET}")
        except Exception as e:
            print(f"{C.RED}Training submission failed: {e}{C.RESET}")

    def cmd_sync(self, args):
        print(f"{C.CYAN}Synchronizing to Knowledge Graph...{C.RESET}")
        synced, verified, total = asyncio.run(self.archive.sync_to_graph())
        print(f"{C.GREEN}[OK] Sync Complete: {synced}/{total} entries internalized.{C.RESET}")

    def cmd_test_notary_skepticism(self, args):
        """End-to-end validation of the Epistemic Firewall."""
        print(f"{C.BOLD}--- Validating Notary Skepticism Layer ---{C.RESET}")
        target = args.target
        print(f"Target Source: {C.CYAN}{target}{C.RESET}")
        
        # 1. Submit Evidence
        payload = {"title": "Anomaly Report", "payload": "Speculative Social Data"}
        print(f"{C.DIM}Submitting speculative pulse...{C.RESET}")
        res = self.inquiry.submit_evidence("test_inquiry", payload, target)
        
        if not res:
            print(f"{C.RED}[ERR] Failed to communicate with Bridge Server.{C.RESET}")
            return

        cid = res.get("id")
        status = res.get("status")
        print(f"Submision Result: CID={cid}, Status={status}")

        # 2. Verify Epistemic Firewall Tagging
        from core.sources import source_validator
        is_volatile = source_validator.is_volatile(target)
        institutional = source_validator.get_source_metadata(target).get("is_institutional")
        vetted = source_validator.get_source_metadata(target).get("is_notary_vetted")

        print(f"\n{C.BOLD}Firewall Metadata Analysis:{C.RESET}")
        print(f"  Institutional Anchor: {institutional}")
        print(f"  Social Volatility:    {is_volatile}")
        print(f"  Notary Vetted:        {vetted}")

        if is_volatile and status == "volatile":
            print(f"\n{C.GREEN}[OK] TEST PASS: Social source correctly tagged as ST_VOLATILE.{C.RESET}")
        elif institutional and status == "speculative":
            print(f"\n{C.GREEN}[OK] TEST PASS: Institutional source correctly staged as SPECULATIVE.{C.RESET}")
        else:
            print(f"\n{C.YELLOW}[WAR]  Manual Verification Required for status: {status}{C.RESET}")

        print(f"\n{C.DIM}Check chronicle.jsonld for immutable ConflictEvents if social override was attempted.{C.RESET}")

    async def run_heartbeat(self, args):
        await self.inquiry.process_heartbeat(args.interval or 30)

    def cmd_onboard(self, args):
        from agents.socratic_onboarder import SocraticOnboarder
        onboarder = SocraticOnboarder()
        asyncio.run(onboarder.run_cli_session())

    def cmd_brief(self, args):
        print(f"{C.CYAN}Synthesizing intelligence brief ({args.hours}h)...{C.RESET}")
        from core.briefing import BriefingEngine
        from agents.reporter import ReporterAgent
        
        engine = BriefingEngine()
        digest = engine.synthesize_digest(hours_back=args.hours)
        
        reporter = ReporterAgent()
        md = asyncio.run(reporter.generate_markdown_report(digest))
        path = reporter.save_report(md)
        print(f"{C.GREEN}[OK] Brief saved to: {path}{C.RESET}")

    def cmd_agenda(self, args):
        from controllers.agenda import AgendaController
        controller = AgendaController()
        if args.seed:
            count = controller.seed_agenda_grains()
            print(f"{C.GREEN}[OK] Generated {count} Truth Seeds from your interest profile.{C.RESET}")
        elif args.approve:
            controller.propose_expansion(args.approve)

    def cmd_hunt(self, args):
        print(f"{C.CYAN}Initiating Manual Hunt Cycle...{C.RESET}")
        from controllers.hunt import HuntController
        from scouts.templates.web_scout import WebScout
        from scouts.base_scout import ScoutConfig
        from storage.auditor_queue import AuditorQueue
        
        scout = WebScout(ScoutConfig(use_proxy=False))
        controller = HuntController(AuditorQueue(), scout)
        
        if args.id:
            asyncio.run(controller.process_seed(args.id))
        else:
            asyncio.run(controller.autonomous_hunt())
        print(f"{C.GREEN}[OK] Hunt Complete.{C.RESET}")

    def cmd_probe(self, args):
        if args.action == "probe":
            print(f"{C.HEADER}🧪 Entering Laboratory: Probing {args.url}...{C.RESET}")
            report = asyncio.run(self.laboratory.probe(args.url))
            
            print(f"\n{C.BOLD}Lab Report:{C.RESET}")
            status_color = C.GREEN if report["status"] == "SUCCESS" else C.RED
            print(f"  Result:      {status_color}{report['status']}{C.RESET}")
            print(f"  Status Code: {report['status_code']}")
            print(f"  Content Len: {report['content_length']} bytes")
            print(f"  Is Document: {report['is_document']}")
            
            if report["obstacles"]:
                print(f"  {C.YELLOW}Obstacles:{C.RESET}   {', '.join(report['obstacles'])}")
            
            print(f"  Findings:    {C.DIM}{report['findings_summary']}{C.RESET}")
            print(f"\n{C.GREEN}[OK] Lab simulation complete.{C.RESET}")

    def cmd_export(self, args):
        print(f"{C.CYAN}Generating Sealed Audit Package (.tar.gz)...{C.RESET}")
        from controllers.export import ExportController
        exporter = ExportController(PROJECT_ROOT)
        path = asyncio.run(exporter.generate_package(cid=args.cid, tag=args.tag))
        if path:
            print(f"{C.GREEN}[OK] Sealed Audit Package saved to: {path}{C.RESET}")
        else:
            print(f"{C.RED}[ERR] Export failed.{C.RESET}")

    def cmd_daemon(self, args):
        if args.action == "start":
            print(f"{C.GREEN}Starting Nexus Daemon in background...{C.RESET}")
            # Ensure top-level logs directory exists
            log_dir = PROJECT_ROOT.parent.parent / "logs"
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / "nexus_daemon.log"
            
            # Use absolute path for daemon.py
            daemon_script = PROJECT_ROOT / "daemon.py"
            subprocess.Popen(
                [sys.executable, str(daemon_script)],
                stdout=open(log_file, "a"),
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
            print(f"{C.DIM}Heartbeat logging to {log_file}{C.RESET}")
        elif args.action == "status":
            log_dir = PROJECT_ROOT.parent.parent / "logs"
            log_file = log_dir / "nexus_daemon.log"
            if log_file.exists():
                print(f"{C.CYAN}Last Daemon Heartbeat:{C.RESET}")
                subprocess.run(["tail", "-n", "5", str(log_file)])
            else:
                print(f"{C.RED}Daemon log not found. Is it running?{C.RESET}")

def main():
    # Fix for Windows encoding issues
    if sys.platform == "win32":
        try:
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        except Exception:
            pass

    bridge = Bridge()
    parser = argparse.ArgumentParser(description="Deep Pulse Bridge")
    subparsers = parser.add_subparsers(dest="command")
    
    subparsers.add_parser("status")
    
    inquiry = subparsers.add_parser("inquiry")
    inquiry.add_argument("--training", action="store_true", help="List archival training tasks")
    
    claim = subparsers.add_parser("claim")
    claim.add_argument("id")
    
    submit = subparsers.add_parser("submit")
    submit.add_argument("id")
    submit.add_argument("payload")
    submit.add_argument("source")
    
    subparsers.add_parser("sync")
    
    train = subparsers.add_parser("train")
    train.add_argument("id", help="Training Inquiry ID")
    train.add_argument("discovery", help="Your forensic finding")
    
    hb = subparsers.add_parser("heartbeat")
    hb.add_argument("--interval", type=int)

    subparsers.add_parser("onboard")
    
    brief = subparsers.add_parser("brief")
    brief.add_argument("--hours", type=int, default=24)
    
    agenda = subparsers.add_parser("agenda")
    agenda.add_argument("--seed", action="store_true")
    agenda.add_argument("--approve", help="Approve an expansion ID")

    hunt = subparsers.add_parser("hunt")
    hunt.add_argument("--id", help="Process a specific seed ID")

    probe = subparsers.add_parser("probe")
    probe.add_argument("--url", required=True)
    probe.add_argument("--action", choices=["probe"], default="probe")

    export = subparsers.add_parser("export")
    export.add_argument("--cid", help="Package a specific CID")
    export.add_argument("--tag", help="Package all entries with this tag/keyword")

    daemon = subparsers.add_parser("daemon")
    daemon.add_argument("action", choices=["start", "status"])

    # Legacy support for --action style (as requested by USER)
    test = subparsers.add_parser("test-notary-skepticism")
    test.add_argument("--target", required=True)

    args = parser.parse_args()
    if args.command == "heartbeat":
        asyncio.run(bridge.run_heartbeat(args))
    elif args.command == "test-notary-skepticism":
        bridge.cmd_test_notary_skepticism(args)
    elif hasattr(bridge, f"cmd_{args.command}"):
        getattr(bridge, f"cmd_{args.command}")(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
