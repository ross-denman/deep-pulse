from flask import Blueprint, jsonify
from datetime import datetime, timezone
from src.notary.core.state_machine import NotaryStateMachine
from src.notary.core.immune_system import NotaryImmuneSystem

board_bp = Blueprint('board', __name__)
state_machine = NotaryStateMachine()
immune_system = NotaryImmuneSystem()

@board_bp.route("/board/sync", methods=["GET"])
def sync_board():
    """
    Public view of the VerificationPool.
    Audit-friendly 'Work Order' feed for the Discovery Mesh.
    """
    open_inquiries = state_machine.list_open_market()
    
    # Enrich inquiries with real-time verify status and friction metrics
    enriched = []
    for inq in open_inquiries:
        inq_id = inq["id"]
        verifiers = state_machine.get_verifiers(inq_id)
        
        # Source Reliability Check (Mocked or pulled from payload metadata)
        # For now, we'll use a default or check if payload exists
        # In a real scenario, the source_url is in the inquiry payload
        
        required = 2 # Default 2+1
        if inq["gravity"] >= 8.0:
            required = 3 # High Gravity / Low Reliability Friction
            
        enriched.append({
            "id": inq_id,
            "title": inq["title"],
            "gravity": inq["gravity"],
            "grain_bounty": inq["grain_bounty"],
            "status": inq["status"],
            "verifier_pool": {
                "current": len(verifiers),
                "required": required,
                "slots_available": max(0, required - len(verifiers))
            },
            "expires_at": inq["expires_at"]
        })
        
    return jsonify({
        "mesh_status": "OPERATIONAL",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "work_orders": enriched
    })
