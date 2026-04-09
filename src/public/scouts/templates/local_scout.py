#!/usr/bin/env python3
"""
Deep Pulse — Local Scout (Manual Ingest)

Specialized scout for local drive 'harvesting'.
Allows human-in-the-loop manual injection of PDFs/Reports.
"""

import logging
import os
import httpx
from typing import List, Dict, Any, Optional
from src.public.scouts.base_scout import BaseScout

logger = logging.getLogger(__name__)

class LocalScout(BaseScout):
    """
    Local Drive Investigator.
    Scouts documents in data/local_ingest/ for distillation.
    """

    async def discover(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manually read local file.
        In Deep Pulse, we point to files relative to data/local_ingest/
        """
        from crawl4ai import BrowserConfig, CrawlerRunConfig, AsyncWebCrawler
        
        filename = params.get("filename") or params.get("url")
        if not filename:
            logger.error("LocalScout: No filename provided in params.")
            return {"markdown": "", "status_code": 404, "error": "No filename"}

        local_path = os.path.abspath(os.path.join("data/local_ingest", filename))
        if not os.path.exists(local_path):
            logger.error(f"LocalScout: File not found at {local_path}")
            return {"markdown": "", "status_code": 404, "error": "File not found"}

        logger.info(f"LocalScout: Ingesting local document {filename}...")
        
        # Direct read for local text/markdown files to avoid Crawl4AI size/structural filters
        if local_path.lower().endswith((".md", ".txt", ".json")):
            logger.info(f"LocalScout: Direct reading text/markdown file: {filename}")
            try:
                with open(local_path, "r") as f:
                    content = f.read()
                return {"markdown": content, "status_code": 200, "error": None}
            except Exception as e:
                logger.error(f"LocalScout: Direct read failed: {e}")
        
        # Fallback to Browser-based ingestion for PDFs/Complex docs
        file_url = f"file://{local_path}"

    async def extract(self, raw_data: str, distiller: Dict[str, Any], keywords: List[str] = None) -> Dict[str, Any]:
        """
        Adaptive RAG Extraction for local files.
        """
        markdown_data = raw_data.get("markdown", "") if isinstance(raw_data, dict) else str(raw_data)
        if not markdown_data:
            return {"confidence": 0.0, "data": {}, "schema_drift": False, "keywords_found": []}

        # Identify found keywords for the Surprise Metric
        found = []
        if keywords:
            for kw in keywords:
                if kw.lower() in markdown_data.lower():
                    found.append(kw)

        logger.info(f"Local Ingest: Distilling via {distiller['model']}...")
        
        try:
            async with httpx.AsyncClient() as client:
                prompt = (
                    "Distill the following MANUALLY INGESTED pulse. Identify data and confidence. "
                    f"Text: {markdown_data[:4000]}"
                )
                resp = await client.post(
                    f"{distiller['base_url']}/api/generate",
                    json={
                        "model": distiller["model"],
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=60.0 # Local ingest might be larger
                )
                distilled = resp.json().get("response", "")
        except Exception as e:
            logger.error(f"Local Ingest distillation failed: {e}")
            distilled = markdown_data[:1000]

        return {
            "confidence": 0.95, # Local manual ingest has high integrity
            "data": distilled,
            "raw_text": markdown_data,
            "keywords_found": found,
            "selectors": {"engine": "local_ingest", "path": "manual_upload"},
            "meta": "Human-Approved Evidence",
            "schema_drift": False
        }

    def mutate_params(self, old_params: Dict[str, Any], hunch: str) -> Dict[str, Any]:
        """Local scouting is usually direct; depth doesn't mutate into other files yet."""
        return old_params
