import asyncio
import logging
import json
import tarfile
import hashlib
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from core.chronicle import read_ledger, verify_entry
from core.identity import load_identity
from core.crypto import sign_data, canonical_json

logger = logging.getLogger("export_controller")

class ExportController:
    """
    Sealed Audit Packages Controller.
    Packages Ledger findings with a verifiable "Chain of Custody" for external disclosure.
    Format: .tar.gz
    """
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.identity = load_identity()
        self.export_dir = self.project_root / "harvest" / "exports"
        self.export_dir.mkdir(parents=True, exist_ok=True)

    async def generate_package(self, cid: Optional[str] = None, tag: Optional[str] = None) -> Optional[Path]:
        """
        Generates a signed .tar.gz audit package.
        """
        ledger = read_ledger()
        entries = []
        
        if cid:
            entries = [e for e in ledger if e["id"] == cid]
        elif tag:
            # Tag search in data or metadata
            entries = [e for e in ledger if tag.lower() in str(e).lower()]
        else:
            # Export all verified entries by default
            entries = [e for e in ledger if e.get("metadata", {}).get("status") == "verified"]

        if not entries:
            logger.warning("No entries found matching export criteria.")
            return None

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        package_name = f"NexusAudit_{timestamp}"
        work_dir = self.export_dir / package_name
        work_dir.mkdir(exist_ok=True)

        try:
            # 1. Create Report & Evidence files
            findings_file = work_dir / "audit_report.json"
            with open(findings_file, "w") as f:
                json.dump(entries, f, indent=2)

            # 2. Generate Manifest
            manifest = {
                "package_id": package_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "node_id": self.identity.outpost_id,
                "entry_count": len(entries),
                "checksums": {
                    "audit_report.json": self._calculate_sha256(findings_file)
                }
            }
            
            # 3. Sign Manifest
            manifest_bytes = canonical_json(manifest)
            manifest["signature"] = self.identity.sign(manifest_bytes)
            
            manifest_file = work_dir / "manifest.json"
            with open(manifest_file, "w") as f:
                json.dump(manifest, f, indent=2)

            # 4. Create .tar.gz
            tar_path = self.export_dir / f"{package_name}.tar.gz"
            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(findings_file, arcname="audit_report.json")
                tar.add(manifest_file, arcname="manifest.json")

            logger.info(f"Sealed Audit Package generated: {tar_path}")
            
            # Cleanup work dir
            import shutil
            shutil.rmtree(work_dir)
            
            return tar_path

        except Exception as e:
            logger.error(f"Failed to generate audit package: {e}")
            return None

    def _calculate_sha256(self, file_path: Path) -> str:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
