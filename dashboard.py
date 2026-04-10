#!/usr/bin/env python3
"""
Deep Ledger - Anomaly Dashboard (dashboard.py)

A premium, web-based Regional Health Monitor UI for 
visualizing Truth Pulses, Swarm performance, and 
identifying high-surprise spikes (Anomalies).
"""

from flask import Flask, render_template_string, jsonify
import json
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
LEDGER_FILE = PROJECT_ROOT / "harvest" / "chronicle.jsonld"

app = Flask(__name__)

# Premium HTML/CSS Dashboard Template
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Deep Ledger | Anomaly Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #090B10;
            --card-bg: rgba(18, 22, 33, 0.7);
            --accent-primary: #00F2FF;
            --accent-secondary: #7000FF;
            --text-main: #E2E8F0;
            --text-dim: #94A3B8;
            --danger: #FF3E6C;
            --warning: #FFAE00;
            --success: #00FF94;
            --glass-border: rgba(255, 255, 255, 0.08);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            background-color: var(--bg);
            color: var(--text_main);
            font-family: 'Outfit', sans-serif;
            overflow-x: hidden;
            background-image: 
                radial-gradient(circle at 50% 50%, rgba(112, 0, 255, 0.05) 0%, transparent 50%),
                radial-gradient(circle at 0% 0%, rgba(0, 242, 255, 0.03) 0%, transparent 40%);
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 3rem;
            border-bottom: 1px solid var(--glass_border);
            padding-bottom: 1.5rem;
        }

        .logo {
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: 2px;
            background: linear-gradient(90deg, var(--accent_primary), var(--accent_secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-family: 'JetBrains Mono', monospace;
        }

        .status-badge {
            background: rgba(0, 255, 148, 0.1);
            color: var(--success);
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 600;
            border: 1px solid rgba(0, 255, 148, 0.2);
            backdrop-filter: blur(5px);
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 2rem;
            margin-bottom: 3rem;
        }

        .card {
            background: var(--card_bg);
            border: 1px solid var(--glass_border);
            border-radius: 24px;
            padding: 2rem;
            backdrop-filter: blur(12px);
            transition: transform 0.3s ease, border-color 0.3s ease;
        }

        .card:hover {
            transform: translateY(-5px);
            border-color: rgba(255, 255, 255, 0.15);
        }

        .card-title {
            color: var(--text_dim);
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 1rem;
        }

        .card-value {
            font-size: 3rem;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
        }

        .pulses-container {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 2rem;
        }

        .pulse-list {
            background: var(--card_bg);
            border: 1px solid var(--glass_border);
            border-radius: 24px;
            padding: 2rem;
        }

        .pulse-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.5rem;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 16px;
            margin-bottom: 1rem;
            border-left: 4px solid var(--accent_primary);
            transition: background 0.3s ease;
        }

        .pulse-item:hover {
            background: rgba(255, 255, 255, 0.05);
        }

        .pulse-id {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
            color: var(--text_dim);
            margin-bottom: 0.25rem;
        }

        .pulse-title {
            font-weight: 600;
            font-size: 1.1rem;
        }

        .anomaly-badge {
            background: rgba(255, 62, 108, 0.1);
            color: var(--danger);
            padding: 0.25rem 0.75rem;
            border-radius: 8px;
            font-size: 0.75rem;
            font-weight: 700;
            border: 1px solid rgba(255, 62, 108, 0.2);
        }

        .surprise-meter {
            width: 100px;
            height: 6px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
            margin-top: 0.5rem;
            position: relative;
        }

        .surprise-fill {
            height: 100%;
            border-radius: 3px;
            background: linear-gradient(90deg, var(--accent_primary), var(--accent_secondary));
        }

        .node-info {
            background: var(--card_bg);
            border: 1px solid var(--glass_border);
            border-radius: 24px;
            padding: 2rem;
        }

        .sidebar-title {
            font-size: 1.2rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
        }

        .info-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 1rem;
            font-size: 0.95rem;
        }

        .label { color: var(--text_dim); }
        .val { font-family: 'JetBrains Mono', monospace; }

        @keyframes pulse-animation {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }

        .live-dot {
            width: 8px;
            height: 8px;
            background: var(--success);
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
            animation: pulse-animation 2s infinite;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">DEEP LEDGER // ANOMALY</div>
            <div class="status-badge"><span class="live-dot"></span>SWARM SYSTEM NOMINAL</div>
        </header>

        <div class="grid">
            <div class="card">
                <div class="card-title">Active Intelligence Pulses</div>
                <div class="card-value" id="val-total">---</div>
            </div>
            <div class="card">
                <div class="card-title">Verified Truth Anchors</div>
                <div class="card-value" id="val-verified" style="color: var(--success)">---</div>
            </div>
            <div class="card">
                <div class="card-title">Anomalies Detected</div>
                <div class="card-value" id="val-anomalies" style="color: var(--danger)">---</div>
            </div>
        </div>

        <div class="pulses-container">
            <div class="pulse-list">
                <h2 style="margin-bottom: 2rem;">Real-time Truth Stream</h2>
                <div id="pulse-stream">
                    <!-- Pulses will be injected here -->
                </div>
            </div>

            <div class="side-bars">
                <div class="node-info" style="margin-bottom: 2rem; border-color: var(--accent-primary);">
                    <div class="sidebar-title" style="color: var(--accent-primary);">⚖️ Inquiry Board</div>
                    <div id="inquiry-board">
                        <div style="font-size: 0.8rem; color: var(--text-dim);">Fetching global work orders...</div>
                    </div>
                </div>

                <div class="node-info" style="margin-bottom: 2rem;">
                    <div class="sidebar-title">Regional Persistence</div>
                    <div class="info-row">
                        <span class="label">Node ID</span>
                        <span class="val" id="node-id">0x0001</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Uptime</span>
                        <span class="val">99.98%</span>
                    </div>
                </div>

                <div class="node-info">
                    <div class="sidebar-title">Intelligence Metabolism</div>
                    <div class="info-row"><span class="label">Power Grid</span><span class="val">NOMINAL</span></div>
                    <div class="info-row"><span class="label">Water Reserve</span><span class="val">STEADY</span></div>
                    <div class="info-row"><span class="label">Gossip Delay</span><span class="val">1.2ms</span></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        async function fetchBoard() {
            try {
                const response = await fetch('/api/board');
                const data = await response.json();
                const container = document.getElementById('inquiry-board');
                
                if (!data.work_orders || data.work_orders.length === 0) {
                    container.innerHTML = '<div style="font-size: 0.8rem; color: var(--text-dim);">No active work orders.</div>';
                    return;
                }

                container.innerHTML = '';
                data.work_orders.forEach(inq => {
                    const el = document.createElement('div');
                    el.style.padding = '1rem';
                    el.style.background = 'rgba(255,255,255,0.02)';
                    el.style.borderRadius = '12px';
                    el.style.marginBottom = '1rem';
                    el.style.border = '1px solid var(--glass-border)';

                    const progress = (inq.verifier_pool.current / inq.verifier_pool.required) * 100;

                    el.innerHTML = `
                        <div style="font-size: 0.7rem; font-family: 'JetBrains Mono'; color: var(--accent-primary); margin-bottom: 0.5rem;">
                            ID: ${inq.id}
                        </div>
                        <div style="font-weight: 600; font-size: 0.9rem; margin-bottom: 0.5rem;">${inq.title}</div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                            <span style="font-size: 0.75rem; color: var(--warning);">🪙 ${inq.grain_bounty} Grains</span>
                            <span style="font-size: 0.75rem; color: var(--text-dim);">${inq.verifier_pool.current}/${inq.verifier_pool.required} Signed</span>
                        </div>
                        <div style="width: 100%; height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px;">
                            <div style="width: ${progress}%; height: 100%; background: var(--success); border-radius: 2px;"></div>
                        </div>
                    `;
                    container.appendChild(el);
                });
            } catch (e) {
                console.error("Board Fetch Failed:", e);
            }
        }

        async function fetchState() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                document.getElementById('val-total').innerText = data.total;
                document.getElementById('val-verified').innerText = data.verified;
                document.getElementById('val-anomalies').innerText = data.anomalies;
                document.getElementById('node-id').innerText = data.outpost_id;

                const stream = document.getElementById('pulse-stream');
                stream.innerHTML = '';
                
                data.recent_pulses.forEach(pulse => {
                    const item = document.createElement('div');
                    item.className = 'pulse-item';
                    if (pulse.is_anomaly) item.style.borderLeftColor = 'var(--danger)';
                    
                    item.innerHTML = `
                        <div>
                            <div class="pulse-id">${pulse.id.substring(0, 32)}...</div>
                            <div class="pulse-title">${pulse.title}</div>
                            <div class="surprise-meter">
                                <div class="surprise-fill" style="width: ${pulse.surprise * 100}%"></div>
                            </div>
                        </div>
                        <div style="text-align: right;">
                            ${pulse.is_anomaly ? '<span class="anomaly-badge">ANOMALY</span>' : ''}
                            <div style="font-size: 0.8rem; color: var(--text-dim); margin-top: 0.5rem;">
                                Score: ${pulse.surprise.toFixed(2)}
                            </div>
                        </div>
                    `;
                    stream.appendChild(item);
                });

            } catch (error) {
                console.error("Dashboard Sync Failed:", error);
            }
        }

        setInterval(fetchState, 5000); // 5s Refresh
        setInterval(fetchBoard, 10000); // 10s Board Refresh
        fetchState();
        fetchBoard();
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route("/api/board")
def board():
    """Proxy the Notary's inquiry board for the dashboard."""
    import requests
    try:
        # Assuming the Notary is on the same host or use env var
        bridge_url = os.environ.get("BRIDGE_URL", "http://localhost:4110")
        resp = requests.get(f"{bridge_url}/board/sync")
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"work_orders": [], "error": str(e)})

@app.route("/api/stats")
def stats():
    if not LEDGER_FILE.exists():
        return jsonify({"total": 0, "verified": 0, "anomalies": 0, "recent_pulses": [], "outpost_id": "0x0000"})
    
    with open(LEDGER_FILE, "r") as f:
        ledger = json.load(f)
    
    verified = sum(1 for e in ledger if e.get("metadata", {}).get("status") == "verified")
    anomalies = sum(1 for e in ledger if e.get("metadata", {}).get("status") == "SILENT_BLOCK" or 
                   (isinstance(e.get("data", {}).get("insight", {}).get("confidence"), float) and e["data"]["insight"]["confidence"] < 0.1))
    
    recent = []
    for e in ledger[-10:]: # Last 10
        title = e.get("data", {}).get("title") or e.get("data", {}).get("type")
        if not title and "insight" in e.get("data", {}):
            title = e["data"]["insight"].get("claim_keyword", "Unknown Pulse")
        
        surprise = 1.0 - e.get("data", {}).get("insight", {}).get("confidence", 0.5) if "insight" in e.get("data", {}) else 0.5
        
        recent.append({
            "id": e["id"],
            "title": title,
            "surprise": surprise,
            "is_anomaly": surprise > 0.8
        })
    
    return jsonify({
        "total": len(ledger),
        "verified": verified,
        "anomalies": anomalies,
        "recent_pulses": recent[::-1], # Reversed for stream
        "outpost_id": ledger[0].get("metadata", {}).get("outpost_id", "0x0001") if ledger else "0x0001"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5173)
