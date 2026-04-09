#!/bin/bash
# The Public Chronicle — Physical Key Handover (physkey.sh)
# 
# Automates the creation of a Granary Snapshot and provides 
# the transfer command for the local "Granary".

C_YELLOW='\033[1;33m'
C_GREEN='\033[0;32m'
C_RESET='\033[0m'

echo -e "${C_YELLOW}🌾 Initiating Physical Key Handover (Primary Engine)...${C_RESET}"

# 1. Run the Snapshotter
# Ensure we include the component roots so "from src..." imports work
export PYTHONPATH=$PYTHONPATH:$(pwd)/deep-ledger:$(pwd)/deep-pulse:.
deep-pulse/.venv/bin/python3 deep-ledger/src/db/vault_snapshot.py

# 1b. Export Outpost Seal Hex for Handover
grep "OUTPOST_KEY=" deep-ledger/.env | cut -d'=' -f2 > deep-ledger/seal_0x0001.hex

# 2. Get the latest snapshot name and create a symlink for easy scp
LATEST_SNAP=$(ls -t deep-ledger/harvest/backups/vault_snapshot_*.tar.gz | head -n 1)
ln -sf "$(pwd)/$LATEST_SNAP" "$(pwd)/deep-ledger/harvest/vault_snapshot_latest.tar.gz"

if [ ! -f "deep-ledger/harvest/vault_snapshot_latest.tar.gz" ]; then
    echo "❌ Error: Snapshot generation failed."
    exit 1
fi

# 3. Get server user and IP
USER_NAME=$(whoami)
# User provided actual IP
SERVER_IP="147.224.166.71"

echo -e "${C_GREEN}✨ Snapshot Created and Linked: deep-ledger/harvest/vault_snapshot_latest.tar.gz${C_RESET}"
echo ""
echo -e "${C_YELLOW}🚀 To move this to your Granary, run this command on your LOCAL machine:${C_RESET}"
echo ""
echo "scp $USER_NAME@$SERVER_IP:$(pwd)/deep-ledger/harvest/vault_snapshot_latest.tar.gz G:/"
echo ""
echo -e "${C_YELLOW}🔑 IMPORTANT: Also copy your Outpost Seal and reputation records to the Physical Key:${C_RESET}"
echo "scp $USER_NAME@$SERVER_IP:$(pwd)/deep-ledger/seal_0x0001.hex G:/seal.hex"
echo "scp $USER_NAME@$SERVER_IP:$(pwd)/deep-ledger/harvest/reputation.json G:/reputation.json"
echo "scp $USER_NAME@$SERVER_IP:$(pwd)/deep-ledger/harvest/heartbeat.log G:/heartbeat.log"
echo ""
echo "Once copied, your Granary Core is safe on your 8GB Physical Key."
