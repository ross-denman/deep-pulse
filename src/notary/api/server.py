from flask import Flask, request, jsonify, send_file
import sys
import os
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta
import logging
from typing import Optional

# Configure global logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("notary_api")

from src.public.core.chronicle import append_entry, read_ledger, add_signature, calculate_consensus_weight
from src.public.core.reputation import ReputationService, ReputationTier
from src.public.core.identity import load_identity
from src.public.core.contracts import ClaimHandshake, ProofOfDiscovery
from src.notary.core.state_machine import NotaryStateMachine
from src.notary.core.immune_system import NotaryImmuneSystem
from src.notary.core.reputation_ledger import NotaryEconomy
from src.notary.api.board import board_bp
from src.notary.core.treasury import Treasury
from functools import wraps

app = Flask(__name__)
app.register_blueprint(board_bp)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "notary-secret")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
LEASE_FILE = PROJECT_ROOT / "harvest" / "leases.json"

class LeaseManager:
    """Manages tactical access permissions for analytical depth."""
    def __init__(self):
        self._load_leases()

    def _load_leases(self):
        if LEASE_FILE.exists():
            with open(LEASE_FILE, "r") as f:
                self.leases = json.load(f)
        else:
            self.leases = {} # auditor_id -> expires_at

    def _save_leases(self):
        LEASE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LEASE_FILE, "w") as f:
            json.dump(self.leases, f, indent=2)

    def purchase_lease(self, auditor_id: str, hours: int = 4) -> Optional[datetime]:
        """Purchase a 4-hour Tactical Lease."""
        cost = 25 # Tactical Lease Cost
        rep_service = ReputationService()
        
        if rep_service.spend_grains(auditor_id, cost, f"Tactical Lease Purchase ({hours}h)"):
            expiry = datetime.now(timezone.utc) + timedelta(hours=hours)
            self.leases[auditor_id] = expiry.isoformat()
            self._save_leases()
            return expiry
        return None

    def has_active_lease(self, auditor_id: str) -> bool:
        """Check if an auditor has a valid, unexpired lease."""
        if auditor_id not in self.leases:
            return False
        
        expiry = datetime.fromisoformat(self.leases[auditor_id])
        if datetime.now(timezone.utc) < expiry:
            return True
        return False

lease_manager = LeaseManager()

identity = load_identity()
state_machine = NotaryStateMachine()
immune_system = NotaryImmuneSystem()
economy = NotaryEconomy()

@app.route("/chronicle", methods=["GET"])
def get_chronicle():
    return jsonify(read_ledger())

def firewall_required(tier: ReputationTier):
    """Decorator to enforce reputation tiers on global endpoints."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            outpost_id = None
            if request.method == "POST":
                outpost_id = request.json.get("outpost_id") or request.json.get("handshake", {}).get("outpost_id")
            elif request.method == "GET":
                outpost_id = request.args.get("outpost_id")
            
            if not outpost_id:
                return "Missing outpost_id", 400
                
            rep_service = ReputationService()
            if not rep_service.check_access(outpost_id, tier):
                return jsonify({
                    "status": "LEVEL_UP_REQUIRED",
                    "message": f"Global access blocked. Status is 'Provisional' (Required Tier: {tier.name}).",
                    "redirect": "/api/v1/training/submit"
                }), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route("/api/v1/training", methods=["GET"])
def list_training():
    """Archival tasks for Provisional training."""
    return jsonify({
        "status": "SANDBOX_ACTIVE",
        "tasks": state_machine.list_training_market()
    })

@app.route("/api/v1/training/submit", methods=["POST"])
def submit_training():
    """Isolated training submission for Seed Grains and Reputation."""
    req = request.json
    if not req: return "Missing training payload", 400
    
    outpost_id = req.get("outpost_id")
    inq_id = req.get("inquiry_id")
    discovery = req.get("discovery", "").strip().upper()
    
    # 1. Retrieve Task & Key
    task = state_machine.get_training_inquiry(inq_id)
    if not task:
        return "Training task not found", 404
        
    answer_key = task["answer_key"].strip().upper()
    rep_service = ReputationService()
    
    # 2. Score Accuracy
    if discovery in answer_key:
        # Success: Reward Seed Grains and Reputation
        # Refined Logic: 1.0 Grain + 0.1 Reputation per task
        rep_service.award_grains(outpost_id, 1, f"Training Reward: {inq_id}")
        new_rep = rep_service.award(outpost_id, "verification", f"Training Mastery: {inq_id}", points=0.1)
        
        return jsonify({
            "status": "TRAINING_SUCCESS",
            "message": "Forensic accuracy verified. Seed Grains awarded.",
            "next_threshold": "1.0 Total REP for AUDITOR promotion (10 tasks total)",
            "current_rep": new_rep
        })
    else:
        # Failure: Apply small humility penalty
        new_rep = rep_service.award(outpost_id, "verification", f"Training Failure: {inq_id}", points=-0.1)
        return jsonify({
            "status": "TRAINING_FAILED",
            "message": "Forensic discrepancy detected. Humility penalty applied.",
            "hint": "Check archival sources more carefully.",
            "current_rep": new_rep
        }), 400

@app.route("/inquiries", methods=["GET"])
def list_inquiries():
    """Returns the open marketplace for Auditors."""
    return jsonify(state_machine.list_open_market())

@app.route("/inquiries/claim", methods=["POST"])
@firewall_required(ReputationTier.SCOUT) # Tier 1+ required to claim global inquiries
def claim_inquiry():
    """
    Accepts a Signed Handshake from an Auditor.
    Enforces liveness gatekeeping and reputation tiers.
    """
    req = request.json
    if not req:
        return "Missing handshake payload", 400
    
    try:
        handshake = ClaimHandshake(**req)
        
        # 1. Cryptographic Validation
        signing_payload = f"{handshake.inquiry_id}{handshake.outpost_id}{handshake.timestamp.isoformat()}"
        if not immune_system.validate_auditor_handshake(handshake.outpost_id, handshake.signature, signing_payload):
            return "Invalid Handshake: Signature failure or low liveness.", 403
            
        # 2. State Transition
        expires_at = state_machine.accept_handshake(handshake)
        if expires_at:
            return jsonify({
                "status": "HANDSHAKE_ACCEPTED",
                "inquiry_id": handshake.inquiry_id,
                "expires_at": expires_at.isoformat()
            })
    except Exception as e:
        logger.error(f"Handshake error: {e}")
        return str(e), 400
            
    return "Inquiry not available or claim failed", 404

@app.route("/inquiries/complete", methods=["POST"])
@firewall_required(ReputationTier.SCOUT)
def complete_inquiry():
    """Submit Proof of Discovery for settlement."""
    req = request.json
    if not req:
        return "Missing discovery proof", 400
        
    try:
        proof = ProofOfDiscovery(**req)
        inq_id = proof.handshake.inquiry_id
        outpost_id = proof.handshake.outpost_id
        
        # 1. Verify Claim Ownership
        current_state = state_machine.get_inquiry(inq_id)
        if not current_state or current_state["claimed_by"] != outpost_id:
            return "Unauthorized: You did not claim this inquiry.", 403
            
        # 2. Verify Payload Integrity
        if not immune_system.validate_proof(outpost_id, proof.payload, proof.handshake.signature):
            return "Invalid Proof: Signature mismatch.", 403
            
        # 3. Transition to VERIFYING status
        state_machine.settle_inquiry(inq_id) # This was the old way
        # New way: Marking as verifying and waiting for mesh consensus
        with state_machine.sqlite3.connect(state_machine.db_path) as conn:
            conn.execute("UPDATE inquiries SET status = 'VERIFYING' WHERE inquiry_id = ?", (inq_id,))
        
        return jsonify({
            "status": "PROMOTED_TO_VERIFYING",
            "message": "Discovery received. Awaiting mesh triangulation (2+1/3+1)."
        })
    except Exception as e:
        logger.error(f"Discovery error: {e}")
        return str(e), 400

@app.route("/inquiries/verify", methods=["POST"])
@firewall_required(ReputationTier.SCOUT)
def verify_claim():
    """Auditors submit attestations to reach consensus."""
    req = request.json
    if not req: return "Missing verification payload", 400
    
    try:
        # Check signature etc via immune_system
        outpost_id = req.get("outpost_id")
        inq_id = req.get("inquiry_id")
        signature = req.get("signature")
        
        # 1. Validation
        if not immune_system.validate_auditor_handshake(outpost_id, signature, f"VERIFY:{inq_id}"):
            return "Invalid Verification: Signature failure or low liveness.", 403
            
        # 2. Add to pool
        if state_machine.add_verification(inq_id, outpost_id, signature):
            # 3. Check for Consensus Completion
            current_inquiry = state_machine.get_inquiry(inq_id)
            source_url = json.loads(current_inquiry["payload"]).get("source_url", "")
            
            required = immune_system.get_required_verifiers(source_url)
            verifiers = state_machine.get_verifiers(inq_id)
            
            if len(verifiers) >= required:
                # Trigger Settlement
                state_machine.settle_inquiry(inq_id)
                return jsonify({"status": "SETTLED", "consensus": "REACHED"})
                
            return jsonify({"status": "VERIFICATION_LOGGED", "current_pool": len(verifiers)})
            
    except Exception as e:
        logger.error(f"Verification error: {e}")
        return str(e), 400
    
    return "Verification failed or inquiry not found", 404

@app.route("/api/v1/notary/lease", methods=["POST"])
def purchase_lease():
    """Endpoint for purchasing tactical access."""
    req = request.json
    auditor_id = req.get("outpost_id")
    if not auditor_id:
        return "Missing outpost_id", 400
        
    expiry = lease_manager.purchase_lease(auditor_id)
    if expiry:
        return jsonify({
            "status": "LEASE_ACTIVE",
            "expires_at": expiry.isoformat(),
            "tier": "TACTICAL_DETECTIVE"
        })
    return "Insufficient Grain balance for Tactical Lease.", 402

@app.route("/api/v1/analysis/forensic-export", methods=["GET"])
def forensic_export():
    """Gated forensic export for depth research."""
    auditor_id = request.args.get("outpost_id")
    if not auditor_id:
        return "Missing outpost_id", 400
        
    # Sovereign Notary is always exempt
    if auditor_id == "TREASURY" or ReputationService().check_access(auditor_id, ReputationTier.SOVEREIGN_NOTARY):
        pass
    elif not lease_manager.has_active_lease(auditor_id):
        return jsonify({
            "error": "LEASE_REQUIRED",
            "message": "This endpoint requires a 'Detective Lease' (25 Grains)."
        }), 403
        
    # Logic for actual export would go here (e.g., calling ExportController)
    return jsonify({"status": "AUTHORIZED", "package": "audit_findings_sealed.tar.gz"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4110)
