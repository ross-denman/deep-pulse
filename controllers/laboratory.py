import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import sys
import os

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scouts.templates.web_scout import WebScout
from scouts.base_scout import ScoutConfig

logger = logging.getLogger("laboratory_controller")

class LaboratoryController:
    """
    The 'Laboratory' Phase Controller.
    Used for targeted testing of scouts against complex targets.
    Supports Proxy Rotation, PDF Extraction, and Captcha Analysis.
    """
    def __init__(self, scout: Optional[WebScout] = None):
        if not scout:
            # Default Lab Configuration
            from scouts.base_scout import ScoutConfig
            config = ScoutConfig(use_proxy=True) # Enable Tor by default for Lab
            
            # Stubs to satisfy BaseScout
            class StubEconomy: 
                def spend_credit(self): return True
            class StubMemory:
                def record_episode(self, p, m): return 0
                def update_path(self, e, a): pass
                def update_reward(self, e, r): pass
                def save_successful_metadata(self, e, m): pass
            
            self.scout = WebScout(
                perimeter="LAB_PROBE",
                config_manager=config,
                economy_manager=StubEconomy(),
                memory_manager=StubMemory()
            )
        else:
            self.scout = scout

    async def probe(self, url: str) -> Dict[str, Any]:
        """
        Execute a targeted probe on a single URL.
        Logs Proxy details, PDF status, and Captcha 'Quenching'.
        """
        logger.info(f"🧪 LABORATORY: Testing target {url}")
        
        # Determine if it's a document
        is_doc = url.lower().endswith(".pdf") or url.lower().endswith(".docx")
        params = {
            "url": url,
            "type": "document" if is_doc else "web",
            "stealth_pre_scout": True # Always use stealth in Lab
        }

        # 1. Discover Phase (Crawl4AI)
        logger.info("Step 1: Discovering (Active Scraping)...")
        raw_data = await self.scout.discover(params)
        
        status_code = raw_data.get("status_code", 200)
        error = raw_data.get("error")
        content_len = len(raw_data.get("markdown", ""))
        
        # 2. Obstacle Analysis
        obstacles = []
        if status_code == 403:
            obstacles.append("CAPTCHA_OR_WAF_BLOCK")
            logger.warning("[WAR] QUENCHED: Probe blocked by Captcha or WAF.")
        elif is_doc and content_len < 300:
            obstacles.append("PDF_EXTRACTION_FAILURE")
            logger.warning("[WAR] PDF_FAIL: Minimal content extracted from document.")
        
        # 3. Extraction/Distillation Phase
        logger.info("Step 2: Extracting (AI Distillation)...")
        distiller = {"model": "lab-distill", "base_url": "internal"}
        findings = await self.scout.extract(raw_data, distiller)
        
        # Analysis Report
        report = {
            "url": url,
            "status": "SUCCESS" if not error and status_code == 200 else "FAILED",
            "status_code": status_code,
            "content_length": content_len,
            "is_document": is_doc,
            "obstacles": obstacles,
            "schema_drift": findings.get("schema_drift", False),
            "findings_summary": str(findings.get("data", ""))[:200] + "..." if findings.get("data") else "None"
        }
        
        return report
