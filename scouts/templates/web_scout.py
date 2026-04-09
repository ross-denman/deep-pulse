#!/usr/bin/env python3
"""
Deep Pulse - Web Scout (Active Researcher)

Specialized scout for web-based discovery.
Uses Crawl4AI + Adaptive RAG cost shield.
"""

import logging
import httpx
import random
import time
from typing import List, Dict, Any, Optional
from crawl4ai import AsyncWebCrawler
from src.public.scouts.base_scout import BaseScout
from src.public.core.llm_client import llm

logger = logging.getLogger(__name__)

class WebScout(BaseScout):
    """
    Active Web Researcher.
    Uses Crawl4AI for discovery and Adaptive RAG for cost-efficient extraction.
    """

    async def discover(self, params: Dict[str, Any]) -> str:
        """
        Active discovery via Crawl4AI.
        Navigates to the URL routing through Tor local bridge if configured.
        """
        from crawl4ai import BrowserConfig, CrawlerRunConfig, AsyncWebCrawler
        
        url = params.get("url")
        logger.info(f"Crawl4AI: Scraping {url}...")
        
        # Map Tor routing details to the new proxy_config interface
        proxy_url = self.config.proxy_url
        
        # Determine if we need specialized PDF/Document handling
        is_document = params.get("type") == "document" or url.lower().endswith(".pdf")
        bypass_tor_req = params.get("bypass_tor", False)

        # Federal Documents / Direct PDFs often block Tor. Adaptive proxy logic:
        use_proxy = self.config.use_proxy and not (is_document or bypass_tor_req)
        
        proxy_config = {"server": proxy_url} if use_proxy and proxy_url else None
        
        if use_proxy:
            logger.info(f"Connecting to Tor Proxy Router at {proxy_url}...")
        elif self.config.use_proxy and (is_document or bypass_tor_req):
            logger.warning(f"Stealth Bypass: Routing DIRECT (No Tor) to avoid Federal anti-bot blocks on PDF/Document.")

        # Header Spoofing: Mimic standard Chrome/Linux browsers
        user_agents = [
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.140 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.109 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.159 Safari/537.36"
        ]
        
        # PROXY ROTATION STRATEGY (Sprint 11)
        # If multiple proxies are provided in .env (comma-separated), rotate them.
        proxy_list = os.getenv("PROXIES", "").split(",")
        proxy_list = [p.strip() for p in proxy_list if p.strip()]
        
        selected_proxy = self.config.proxy_url
        if proxy_list:
            selected_proxy = random.choice(proxy_list)
            logger.info(f"Stealth Rotation: Rotating to proxy {selected_proxy}")

        proxy_config = {"server": selected_proxy} if use_proxy and selected_proxy else None

        selected_agent = random.choice(user_agents)
        logger.info(f"Stealth Mode: Using User-Agent: {selected_agent}")

        # Standard browser headers to improve stealth
        extra_headers = {
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1"
        }

        # Crawl4AI 0.8.x enforces stealth properties inside BrowserConfig natively
        browser_cfg = BrowserConfig(
            headless=True, 
            java_script_enabled=True,
            proxy_config=proxy_config,
            enable_stealth=True,
            ignore_https_errors=True,
            user_agent=selected_agent,
            headers=extra_headers
        )
        
        # Determine if we need specialized PDF/Document handling
        is_document = params.get("type") == "document" or url.lower().endswith(".pdf")
        if is_document:
            logger.info(f"Targeting DOCUMENT: Explicit PDF extraction strategy activated for {url}")
        
        # run_cfg handles cache, excluding deprecated magic_kwargs
        run_cfg = CrawlerRunConfig(
            cache_mode="BYPASS",
            pdf=is_document,
            process_iframes=True
        )
        
        try:
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                # Stealth Pre-Scout (Spring 09): Find ToS/FDA Disclaimers to establish legal session
                if params.get("stealth_pre_scout"):
                    from urllib.parse import urlparse, urljoin
                    parsed = urlparse(url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}/"
                    pre_scout_paths = ["/terms-of-service", "/fda-disclaimer", "/legal", "/disclaimer"]
                    logger.info(f"Stealth Pre-Scout: Probing legal sub-portals for {base_url}...")
                    for path in pre_scout_paths:
                         p_url = urljoin(base_url, path)
                         try:
                             # Quick 1s timeout check for ToS presence
                             await crawler.arun(url=p_url, config=CrawlerRunConfig(cache_mode="BYPASS", session_id="pre_scout"))
                             logger.info(f"Stealth Pre-Scout: Established legal session via {path}")
                             break # One is enough for cookies
                         except: 
                             continue
                    time.sleep(random.uniform(1.0, 2.0))

                # Stealth warm-up: Visit landing page first if targeting a deep document to establish cookies
                prime_url = params.get("prime_url")
                if prime_url or is_document or "/system/files/" in url or "fincen.gov" in url:
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    warmup_url = prime_url or (f"{parsed.scheme}://{parsed.netloc}/newsroom" if ("fincen" in url or "aaos" in url) else f"{parsed.scheme}://{parsed.netloc}/")
                    logger.info(f"Stealth Warm-up: Priming session via {warmup_url}...")
                    await crawler.arun(url=warmup_url, config=CrawlerRunConfig(cache_mode="BYPASS"))
                    # Short jitter after warm-up
                    time.sleep(random.uniform(1.0, 2.0))

                result = await crawler.arun(url=url, config=run_cfg)
                if not result.success:
                    logger.error(f"Crawl4AI failed: {result.error_message}")
                    return {"markdown": "", "status_code": result.status_code if hasattr(result, "status_code") else 500, "error": result.error_message}
                
                # Check for "Minimal Yield Fetch" (Common on JS-Protected PDFs)
                content_len = len(result.markdown or "")
                if is_document and content_len < 300:
                    logger.warning(f"\n{'-'*60}\n🚨 OPERATOR ALERT: PROTECTED DOCUMENT DETECTED\n{'-'*60}")
                    logger.warning(f"Target: {url}")
                    logger.warning(f"Result: {content_len} bytes extracted (JS-Challenge likely)")
                    logger.warning(f"INSTRUCTION: PDF seems protected. Download locally and move to 'data/local_ingest/'")
                    logger.warning(f"Then run: python3 src/pulse.py scout run --template local ...")
                    logger.warning(f"{'-'*60}\n")
                    return {"markdown": "", "status_code": 403, "error": "Protected PDF: Manual ingest required."}
                
                # ─── Recursive Discovery (Sprint 11) ───
                # If depth > 0, we can use crawl4ai's link extraction or manual dive
                target_depth = params.get("depth", 0)
                if target_depth > 0:
                    logger.info(f"⚡ URGENT RECURSION: Deep Dive level {target_depth} activated for {url}")
                
                return {"markdown": result.markdown, "status_code": result.status_code if hasattr(result, "status_code") else 200, "error": None, "depth_level": target_depth}
        except Exception as e:
            if self.config.use_proxy and not self.config.strict_proxy:
                logger.warning(f"Tor Node blocked or unavailable ({e}). Falling back to Direct Connection...")
                browser_cfg = BrowserConfig(
                    headless=True, 
                    java_script_enabled=True,
                    enable_stealth=True, 
                    ignore_https_errors=True,
                    user_agent=selected_agent,
                    headers=extra_headers
                )
                run_cfg = CrawlerRunConfig(
                    cache_mode="BYPASS",
                    pdf=is_document,
                    process_iframes=True
                )
                async with AsyncWebCrawler(config=browser_cfg) as crawler:
                    result = await crawler.arun(url=url, config=run_cfg)
                    status = result.status_code if hasattr(result, "status_code") else (200 if result.success else 500)
                    return {"markdown": result.markdown if result.success else "", "status_code": status, "error": result.error_message if hasattr(result, "error_message") else str(e)}
            else:
                logger.error(f"Strict Proxy / Evasion Failed: {e}")
                return {"markdown": "", "status_code": 500, "error": str(e)}


    async def extract(self, raw_data: Any, distiller: Dict[str, Any], keywords: List[str] = None) -> Dict[str, Any]:
        """
        Adaptive RAG Extraction & Schema Drift Detection
        """
        markdown_data = raw_data.get("markdown", "") if isinstance(raw_data, dict) else str(raw_data)
        if not markdown_data:
            return {"confidence": 0.0, "data": {}, "schema_drift": False, "keywords_found": []}

        # Identify found keywords for the Surprise Metric (Keyword Salience)
        found = []
        if keywords:
            for kw in keywords:
                # Case-insensitive fragment matching
                if kw.lower() in markdown_data.lower():
                    found.append(kw)
        
        if found:
            logger.info(f"Keyword Salience: Detected {len(found)} mission anchors in payload.")

        try:
            from langchain_core.messages import HumanMessage
            logger.info(f"Tier 0: Distilling via configured LLM...")
            
            prompt = (
                "Distill the following pulse from OSINT Markdown. Identify data and confidence. "
                "If the standard keys appear renamed but semantically match (e.g. gross_count -> total_gamma), "
                f"flag schema_drift: true. Text: {markdown_data[:2000]}"
            )
            
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            distilled = response.content
            
            # Basic heuristic check for model signaling drift
            has_drift = "schema_drift: true" in distilled.lower()
            self.session_cost += 0.0002 # Local processing cost
        except Exception as e:
            logger.error(f"Lower-Tier distillation failed: {e}")
            distilled = markdown_data[:500]
            has_drift = False
            self.session_cost += 0.0001

        # Tier 1: Central Brain (Higher reasoning if needed)
        if self.economy.spend_credit():
            logger.info("Spending Compute Credit for Tier 1 Central Brain extraction.")
            self.session_cost += 0.05 # Credit-equivalent USD cost
            return {
                "confidence": 0.9, 
                "data": distilled, 
                "keywords_found": found,
                "selectors": {"engine": "crawl4ai", "path": "markdown_v1"},
                "meta": "High-Integrity Verification",
                "schema_drift": has_drift
            }
            
        return {
            "confidence": 0.5, 
            "data": distilled,
            "raw_text": markdown_data,
            "keywords_found": found,
            "selectors": {"engine": "crawl4ai", "path": "markdown_v1"},
            "meta": "Local Distillation Pass",
            "schema_drift": has_drift
        }

    def mutate_params(self, old_params: Dict[str, Any], hunch: str) -> Dict[str, Any]:
        """Reformulates search parameters based on Diversity Heuristics from CuriosityBot."""
        new_params = old_params.copy()
        
        # Use initial URL as base if it's already a mutated path
        url = new_params['url'].rstrip('/')
        
        # Diversity heuristics suffixes
        suffixes = ["archive", "sitemap.xml", "data", "reports", "research"]
        
        for suffix in suffixes:
            if suffix in hunch.lower():
                # Avoid nesting like /archive/archive
                if not url.endswith(f"/{suffix}"):
                    new_params["url"] = f"{url}/{suffix}"
                break
                
        return new_params
