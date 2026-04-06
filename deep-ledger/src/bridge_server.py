from flask import Flask, request, jsonify
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path("/home/ubuntu/deep-ledger")
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.ledger import append_entry, verify_entry, read_ledger
from src.core.reputation import ReputationService, ReputationTier
from src.core.identity import load_identity

app = Flask(__name__)
rep_service = ReputationService()
identity = load_identity()

@app.route("/ledger", methods=["GET"])
def get_ledger():
    return jsonify(read_ledger())

@app.route("/ledger", methods=["POST"])
def post_ledger():
    entry = request.json
    if not entry:
        return "Missing entry", 400
    
    # 1. Verify cryptographic integrity
    if not verify_entry(entry):
        return "Invalid signature", 401
    
    # 2. Append to local JSON-LD
    append_entry(entry)
    
    # 3. Update reputation for discovery (if verified status already exists)
    node_id = entry.get("metadata", {}).get("node_id")
    if node_id:
        rep_service.register_node(node_id, entry["proof"]["verificationMethod"])
        if entry.get("metadata", {}).get("status") == "verified":
             rep_service.award(node_id, "discovery", f"Verified discovery for {entry['id']}")
    
    return jsonify({"id": entry["id"], "status": "recorded"})

@app.route("/status/<node_id>", methods=["GET"])
def get_status(node_id):
    node = rep_service.get_node(node_id)
    if not node:
        return "Node not found", 404
    return jsonify({
        "score": node.score,
        "tier": node.tier_name,
        "compute_credits": node.compute_credits
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4110)
