from flask import Flask, request, jsonify, send_file
import sys
import os
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta
import logging

# Configure global logging for the Notary Bridge
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("bridge_server")
from src.public.core.chronicle import append_entry, verify_entry, read_ledger, add_signature, calculate_consensus_weight, create_entry
from src.public.core.reputation import ReputationService, ReputationTier
from src.public.core.identity import load_identity
from flask_socketio import SocketIO, emit
from src.private.security import security_bridge
from src.public.core.sources import source_validator
from src.public.controllers.consensus import ConsensusController
from src.private.master_queue import MasterOutpostQueue

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "notary-secret")
socketio = SocketIO(app, cors_allowed_origins="*")

identity = load_identity()
queue = MasterOutpostQueue()

# Initialize Consensus Policy
from src.public.core.network import MeshClient
client = MeshClient("http://localhost:4110") # Loopback to self for policy layer
consensus_controller = ConsensusController(client, identity, security_bridge.rep_service)

# In-memory storage for MVP (Deprecated in favor of SQLite MasterQueue)
# INQUIRIES = [...]
TTS_LEASE_HOURS = 24

@app.route("/chronicle", methods=["GET"])
def get_chronicle():
    # Apply Fog of War if an outpost_id is provided
    outpost_id = request.args.get("outpost_id")
    chronicle = read_ledger()
    if outpost_id:
        entries = [security_bridge.apply_fog_of_war(entry, outpost_id) for entry in chronicle]
        return jsonify([e for e in entries if e is not None])
    return jsonify(chronicle)

@app.route("/chronicle", methods=["POST"])
def post_chronicle():
    payload = request.json or {}
    
    # 1. Authoritative State Validation (Anti-Cheat)
    # Extract identity and entry from potentially nested payload
    if "entry" in payload:
        entry = payload["entry"]
        outpost_id = payload.get("outpost_id")
        signature = payload.get("signature")
    else:
        entry = payload
        outpost_id = None
        signature = None

    # Robust Identity Extraction from Internal Metadata/Proof
    proof = entry.get("proof", {})
    if not outpost_id:
        # Check signatures array first
        signatures = proof.get("signatures", [])
        if signatures:
            outpost_id = signatures[0].get("outpost_id")
            signature = signatures[0].get("seal")
        else:
            outpost_id = entry.get("metadata", {}).get("outpost_id")
            signature = proof.get("seal") or proof.get("signature")

    # Includes seal check, velocity limit, and CID friction
    if not security_bridge.validate_submission(outpost_id, entry, signature):
        return "Submission rejected by Security Bridge (Integrity/Velocity/Sovereignty)", 403
    
    # 2. Duplicate Check: If CID exists, this might be a signature addition
    chronicle = read_ledger()
    existing_entry = next((e for e in chronicle if e["id"] == entry["id"]), None)
    
    if existing_entry:
        # Check if this is a new seal for an existing entry
        if add_signature(existing_entry, security_bridge.rep_service.get_outpost(outpost_id)):
            # Epistemic Firewall: Multi-Stage Weighting
            weight = calculate_consensus_weight(existing_entry, security_bridge.rep_service)
            status = existing_entry.get("metadata", {}).get("status", "speculative")
            
            # Use higher threshold for volatile sources
            threshold = 1.0 if status != "volatile" else 1.5 # 1.5 req. higher quorum (3+1 scouts)
            
            if weight >= threshold:
                existing_entry["metadata"]["status"] = "verified"
            
            # Save updated chronicle
            PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
            CHRONICLE_FILE = PROJECT_ROOT / "harvest" / "chronicle.jsonld"
            with open(CHRONICLE_FILE, "w") as f:
                json.dump(chronicle, f, indent=2, ensure_ascii=False)
            
            return jsonify({"id": entry["id"], "status": existing_entry["metadata"]["status"], "weight": weight})
        return "Seal already exists or invalid", 400

    # 3. Epistemic Conflict Detection
    conflict_event = consensus_controller.check_conflicts(entry)
    if conflict_event:
        append_entry(conflict_event)
        logger.warning(f"Notarized ConflictEvent: {conflict_event['id']}")

    # 4. Append to local JSON-LD (New Entry)
    append_entry(entry)
    
    # 4. Update reputation for discovery (if verified status already exists)
    if outpost_id:
        # Register if new (though validate_submission requires registration)
        security_bridge.rep_service.register_outpost(outpost_id, entry["proof"]["signatures"][0]["verificationMethod"])
        if entry.get("metadata", {}).get("status") == "verified":
             security_bridge.rep_service.award(outpost_id, "discovery", f"Verified discovery for {entry['id']}")
    
    return jsonify({"id": entry["id"], "status": "recorded"})
    
@app.route("/status/<outpost_id>", methods=["GET"])
def get_status(outpost_id):
    outpost = security_bridge.rep_service.get_outpost(outpost_id)
    if not outpost:
        return "Outpost not found", 404
    return jsonify({
        "score": outpost.score,
        "trust": outpost.trust_score,
        "tier": outpost.tier_name
    })
    
@app.route("/vault/snapshot", methods=["POST"])
def get_vault_snapshot():
    """Gated endpoint for Anchor Outposts to request a full encrypted snapshot."""
    msg = request.json
    if not msg:
        return "Missing identity proof", 400
    
    outpost_id = msg.get("outpost_id")
    signature = msg.get("signature") # Seal of "REQUEST_SNAPSHOT"
    
    # 1. Identity & Reputation Check
    outpost_rep = security_bridge.rep_service.get_outpost(outpost_id)
    if not outpost_rep or outpost_rep.tier < ReputationTier.AUDITOR:
        return "Sovereign Hands Denied: Requires Tier 2 (Auditor) Merit.", 403
    
    # 2. Verify Seal
    from src.public.core.identity import verify_signature_with_pubkey
    if not verify_signature_with_pubkey(outpost_rep.public_key_hex, b"REQUEST_SNAPSHOT", signature):
        return "Invalid seal for snapshot request.", 401

    # 3. Generate & Serve Snapshot
    from src.db.vault_snapshot import VaultSnapshotter
    snapshotter = VaultSnapshotter()
    anchor_path = snapshotter.create_encrypted_anchor_snapshot(outpost_id)
    
    return send_file(anchor_path, as_attachment=True)

from src.public.core.p2p import p2p # Global P2P instance

@app.route("/chronicle/sign", methods=["POST"])
def sign_chronicle_entry():
    """Endpoint for outposts to contribute a seal to an existing CID."""
    req = request.json
    if not req or "cid" not in req or "outpost_id" not in req:
        return "Missing cid or outpost_id", 400
    
    cid = req["cid"]
    outpost_id = req["outpost_id"]
    
    # 1. Identity & Reputation Check
    outpost_rep = security_bridge.rep_service.get_outpost(outpost_id)
    if not outpost_rep or outpost_rep.tier < ReputationTier.PROBE:
        return "Sovereign Hands Denied: Requires Tier 1 (Probe) Merit.", 403
        
    # 2. Find entry
    chronicle = read_ledger()
    entry = next((e for e in chronicle if e["id"] == cid), None)
    if not entry:
        return "CID not found in chronicle", 404
        
    # 3. Hand-off to post_chronicle for seal aggregation logic 
    if add_signature(entry, OutpostIdentity(key_hex=outpost_rep.public_key_hex, outpost_id=outpost_id)):
        # Identify institutional anchors
        source_url = entry.get("metadata", {}).get("source_url", "")
        source_meta = source_validator.get_source_metadata(source_url)
        
        weight = calculate_consensus_weight(entry, security_bridge.rep_service)
        status = entry.get("metadata", {}).get("status", "speculative")
        
        # Enforce threshold
        threshold = 1.0 if status != "volatile" else 1.5 
        
        if weight >= threshold:
            # "Hand of the Anchor": Prevent status-flip of institutional data via social noise
            if source_meta.get("is_institutional"):
                entry["metadata"]["status"] = "verified"
            else:
                # If it's volatile, it needs that high weight
                entry["metadata"]["status"] = "verified"
            
            # Award Grains for verification if it pushes to verification
            security_bridge.rep_service.award(outpost_id, "verification", f"Consensus reached for {cid}")
        
        # Save updated chronicle
        PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
        CHRONICLE_FILE = PROJECT_ROOT / "harvest" / "chronicle.jsonld"
        with open(CHRONICLE_FILE, "w") as f:
            json.dump(chronicle, f, indent=2, ensure_ascii=False)
            
        return jsonify({"id": cid, "status": entry["metadata"]["status"], "weight": weight})
        
    return "Failed to add seal", 400


@app.route("/p2p/discover", methods=["POST"])
def p2p_discover():
    """Endpoint for other outposts to announce themselves."""
    msg = request.json
    if not msg:
        return "Missing message", 400
    
    # Let P2PManager handle the message (verify sig, update peer map)
    asyncio.run(p2p.handle_incoming_message(json.dumps(msg)))
    return jsonify({"status": "discovered"})

@app.route("/p2p/manifest", methods=["GET"])
def p2p_manifest():
    """Returns a list of all known CIDs for peer synchronization."""
    p2p._refresh_cid_cache()
    return jsonify(list(p2p.known_cids))

@app.route("/p2p/gossip", methods=["POST"])
def p2p_gossip():
    """Endpoint for propagating Alpha Alerts (new CIDs)."""
    msg = request.json
    if not msg:
        return "Missing message", 400
    
    asyncio.run(p2p.handle_incoming_message(json.dumps(msg)))
    return jsonify({"status": "propagated"})

@app.route("/inquiries", methods=["GET"])
def list_inquiries():
    """Returns a list of all open inquiries."""
    return jsonify([i for i in queue.list_open_inquiries()])

@app.route("/inquiries/claim", methods=["POST"])
def claim_inquiry():
    """Allows an outpost to claim an inquiry with a TTS lease."""
    req = request.json
    if not req or "inquiry_id" not in req or "outpost_id" not in req:
        return "Missing inquiry_id or outpost_id", 400
        
    inq_id = req["inquiry_id"]
    outpost_id = req["outpost_id"]
    
    # 1. Reputation Check
    outpost_rep = security_bridge.rep_service.get_outpost(outpost_id)
    if not outpost_rep or outpost_rep.tier < ReputationTier.SCOUT:
        return "Low Reputation: Requires Tier 1 (Scout) to claim high-gravity inquiries.", 403
        
    # 2. Claim via Queue
    expires_at = queue.claim_grain(inq_id, outpost_id, lease_hours=TTS_LEASE_HOURS)
    if expires_at:
        return jsonify({
            "status": "claimed",
            "inquiry_id": inq_id,
            "expires_at": expires_at
        })
            
    return "Inquiry ID not found or already claimed", 404

@app.route("/inquiries/complete", methods=["POST"])
def complete_inquiry():
    """Submit results for a claimed inquiry and receive Grains."""
    req = request.json
    if not req or "inquiry_id" not in req or "outpost_id" not in req or "payload" not in req:
        return "Missing inquiry_id, outpost_id, or payload", 400
        
    inq_id = req["inquiry_id"]
    outpost_id = req["outpost_id"]
    
    # Note: In a real implementation, we'd check the DB for claim status
    # For now, we allow the completion if the queue marks it as success
    
    # 1. Process Payload (Verification logic would go here)
    # For MVP, we assume any payload is a valid grain submission
    
    # 2. Award Grains & Reputation
    reward = 25 # Default reward
    security_bridge.rep_service.award_grains(outpost_id, reward, f"Completed Inquiry: {inq_id}")
    security_bridge.rep_service.award(outpost_id, "verification", f"Successful inquiry resolution for {inq_id}")
    
    queue.complete_grain(inq_id)
    
    return jsonify({
        "status": "rewarded",
        "grains": reward
    })
            
    return "Inquiry ID not found or not claimed by you", 404

    if queue.enqueue_grain(req["id"], req["title"], req["payload"], gravity, probe_id):
        return jsonify({"status": "staged", "id": req["id"]})
    return "Grain already staged or error", 409

# ─── Anonymous Drop Gate (Sprint 11) ──────────────────────────────

@app.route("/pulse/challenge", methods=["GET"])
def get_pow_challenge():
    """Returns a PoW challenge for anonymous drops."""
    outpost_id = request.args.get("outpost_id", "anonymous")
    challenge = security_bridge.generate_pow_challenge(outpost_id)
    return jsonify(challenge)

@app.route("/pulse/drop", methods=["POST"])
def pulse_drop():
    """Anonymous Pulse submission gateway with Hash Puzzle PoW protection."""
    req = request.json
    if not req or "payload" not in req or "pow" not in req:
        return "Missing pulse payload or Proof-of-Work", 400
    
    # 1. Verify Hash Puzzle
    pow_data = req["pow"]
    salt = pow_data.get("salt")
    nonce = pow_data.get("nonce")
    difficulty = pow_data.get("difficulty")
    
    if not security_bridge.verify_hash_puzzle(salt, nonce, difficulty):
        return "Invalid Proof-of-Work: Hash Puzzle Failure.", 403
    
    # 2. Package as Unverified Drop
    from src.public.core.crypto import compute_cid
    payload = req["payload"]
    title = payload.get("title", "Anonymous Drop")
    source = payload.get("source", "anonymous_drop")
    
    # Generate temporary ID
    grain_id = f"drop_{datetime.now(timezone.utc).timestamp()}"
    
    # 3. Enqueue for Audit
    if queue.enqueue_grain(grain_id, title, payload, source_chaff=source, gravity=3.0, probe_id="ANONYMOUS_GATEWAY"):
        logger.info(f"Accepted anonymous drop: {grain_id}")
        return jsonify({"status": "accepted", "id": grain_id})
        
    return "Drop processing failed", 500

if __name__ == "__main__":
    # Start background metabolism: Grains Yield & P2P Loops
    import threading
    import time
    def start_background_tasks():
        import asyncio
        # Start P2P loops
        asyncio.run(p2p.start())
        
        # Start Metabolism Loop (Daily Yield Automation)
        while True:
            logger.info("⏳ Core Metabolism: Applying global Grains yield distribution.")
            security_bridge.rep_service.apply_yield_to_all()
            time.sleep(3600) # Once per hour for "Fast-Forward" simulation
    
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
         threading.Thread(target=start_background_tasks, daemon=True).start()

    socketio.run(app, host="0.0.0.0", port=4110, allow_unsafe_werkzeug=True)
