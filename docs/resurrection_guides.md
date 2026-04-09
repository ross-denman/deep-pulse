# Resurrection Guides — The "Institutional Mind" Protocol

> "A standard only exists if it can be rebuilt from zero."

This guide explains how to restore the Deep Ledger outpost, its Knowledge Graph, and its Intelligence Vault from a sovereign backup. This is critical for anti-fragility, hardware migration (e.g., to a new Curiosity Outpost), or disaster recovery.

## 🛡️ The Anatomy of a Resurrection

When you "resurrect" an outpost, you are performing two distinct operations:
1.  **Vault Restoration**: Restoring the raw, cryptographically signed `chronicle.jsonld`.
2.  **Knowledge Reconstruction**: Re-running the `rebuild_graph.py` utility to populate a fresh Neo4j database from the ledger.

---

## 🏗️ Rebuilding the Graph (`rebuild_graph.py`)

If your database is corrupted or you are setting up a fresh outpost, use the Resurrection Layer to reconstruct the Knowledge Graph.

### Prerequisites
- Neo4j must be running (`docker-compose up -d`).
- Your `harvest/chronicle.jsonld` must be present.

### Standard Reconstruction
```bash
# From the project root
python deep-ledger/src/db/rebuild_graph.py
```

### USB Physical Key Resurrection
If you are moving your "Institutional Mind" to a new device via a USB key:
1.  Mount the USB key (e.g., to `/mnt/usb`).
2.  Run the rebuilder pointing to the external chronicle:
```bash
python deep-ledger/src/db/rebuild_graph.py --chronicle /mnt/usb/soul-ledger/harvest/chronicle.jsonld
```

---

## 📦 Vault Snapshots (`vault_snapshot.py`)

The Vault Snapshotter handles automated backups, pruning, and encrypted handovers.

### Creating a Local Snapshot
```bash
python deep-ledger/src/db/vault_snapshot.py
```
*Snapshots are saved to `harvest/backups/vault_snapshot_YYYYMMDD_HHMMSS.tar.gz`.*

### Creating a USB Backup
To create a snapshot directly to an external drive (your "Physical Key"):
```bash
python deep-ledger/src/db/vault_snapshot.py --destination /mnt/usb/backups/
```

### Encryption & Handover
For Tier 2 Anchor outposts, you can create an encrypted vault mirror:
```bash
# This uses the recipient's Outpost ID to derive an encryption key
python -c "from db.vault_snapshot import VaultSnapshotter; VaultSnapshotter().create_encrypted_anchor_snapshot('OUTPOST_ID_HERE')"
```


---

## 🏛️ The OCI Outpost (The Workbench)

Your "Institutional Mind" currently lives on an **Oracle Cloud (OCI)** Free Tier instance. This provides a high-performance, 24/7 "Primary Engine" for your intelligence audits.

### 🛡️ Why OCI is Great (The World-Class Engine)
*   **OCI Boot Volume Backups**: Before you try a "risky" update in Sprint 04, you can take a **Boot Volume Backup** in the Oracle Cloud Console. If you break the code, you can simply restore the volume, and your chronicle is perfect again.
*   **Sovereign Scale**: You have a world-class engine for $0.00, providing the compute power necessary for deep RAG and graph analysis.
*   **Isolation**: Your OCI Outpost is isolated from your personal machine, providing a "Buffer Zone" for intelligence discovery.

---

## 🔑 The USB Physical Key Strategy (External G: Drive)

To ensure your data is indestructible, use the provided `physkey.sh` utility to move your "Institutional Mind" to your local **G:** drive.

### 🚀 Step 1: Create the Handover Package
On your sovereign OCI Outpost, run:
```bash
./physkey.sh
```
This script will prune redundant signals, generate a verified snapshot, and provide the exact command to download the data to your local machine.

### 📥 Step 2: Transfer to your Local Machine (G:)
Open a command prompt (or PowerShell) on your local Windows machine and run the `scp` command provided by `physkey.sh`. It will look something like this:
```bash
# Example (Run this on YOUR machine, replace with the output of physkey.sh)
scp ubuntu@<SERVER_IP>:/home/ubuntu/soul-ledger/vault_snapshot_latest.tar.gz G:/
```

### 🗝️ Step 3: Identity Backup
Always ensure your `outpost_0x0001.hex` (your private key) is stored on the G: drive alongside the snapshot. This key is your unique "Seal" on the mesh.

---

> [!IMPORTANT]
> **Hardware Failover**: If your primary outpost fails, plug the USB key into the new device. You can then run `rebuild_graph.py --chronicle G:/vault_snapshot_latest.tar.gz` (after extracting) to restore the Institutional Mind.

> [!IMPORTANT]
> Your `private_key.hex` is the ONLY way to continue signing as the same outpost identity. Ensure it is also backed up securely on your Physical Key.
