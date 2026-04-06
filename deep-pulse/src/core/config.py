#!/usr/bin/env python3
"""
Deep Pulse — Config Service (LLM-Agnostic + Adaptive RAG)

Manages provider configuration and enforces cost/time budgets.
Implements the Adaptive RAG cost shield: Tiny local model summarization
before Central Brain (LLM) routing.
"""

import os
import logging
import httpx
from typing import Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages LLM providers and cost budgets."""

    def __init__(self, env_path: str = ".env"):
        load_dotenv(env_path)
        
        # LLM Provider Configuration
        self.llm_provider = os.getenv("LLM_PROVIDER", "local")
        self.llm_model = os.getenv("LLM_MODEL", "llama3")
        self.llm_base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
        
        # Adaptive RAG Cost Shield
        self.max_cost = float(os.getenv("MAX_COST", "2.00"))
        self.max_time = int(os.getenv("MAX_TIME", "300")) # seconds (5 mins)
        
        # Local Distillation Model (for Tier 0 processing)
        self.local_model_enabled = os.getenv("LOCAL_MODEL_ENABLED", "True").lower() == "true"
        self.local_distill_model = os.getenv("LOCAL_DISTILL_MODEL", "qwen3:1.7b")
        self.local_distill_url = os.getenv("LOCAL_DISTILL_URL", "http://localhost:11434")

        # Stealth & Tor Proxy network
        self.use_proxy = os.getenv("USE_PROXY", "False").lower() == "true"
        self.proxy_url = os.getenv("PROXY_URL", "http://127.0.0.1:9050")
        self.strict_proxy = os.getenv("STRICT_PROXY", "False").lower() == "true"

    def get_llm_config(self) -> Dict[str, str]:
        """Returns the configuration for the active LLM provider."""
        config = {
            "provider": self.llm_provider,
            "model": self.llm_model,
            "base_url": self.llm_base_url
        }
        
        # Append API keys based on provider
        if self.llm_provider == "openai":
            config["api_key"] = os.getenv("OPENAI_API_KEY")
        elif self.llm_provider == "anthropic":
            config["api_key"] = os.getenv("ANTHROPIC_API_KEY")
        elif self.llm_provider == "openrouter":
            config["api_key"] = os.getenv("OPENROUTER_API_KEY")
            
        return config

    def check_local_endpoint(self) -> bool:
        """
        Performs a non-blocking health check on the local LLM endpoint.
        Returns True if the service is reachable.
        """
        if not self.local_model_enabled:
            return False

        try:
            # Use the /api/tags or / endpoint for a quick check
            # Strip /v1 if it exists for the raw Ollama check if needed, 
            # but httpx handles the provided URL.
            response = httpx.get(self.local_distill_url.replace("/v1", ""), timeout=0.5)
            return response.status_code == 200
        except (httpx.RequestError, httpx.ConnectError):
            return False

    def get_best_distiller(self) -> Dict[str, Any]:
        """
        Determines the best distiller for Tier 0 processing.
        Returns Local Distiller if enabled and healthy, or falls back to Cloud Mini.
        """
        if self.local_model_enabled and self.check_local_endpoint():
            logger.info(f"Intelligence Gate: Routing Raw Ingestion to LOCAL service ({self.local_distill_model})")
            return {
                "type": "local",
                "model": self.local_distill_model,
                "base_url": self.local_distill_url
            }
        
        # Fallback to main LLM if local is unavailable
        logger.warning("Intelligence Gate: Local distiller unavailable. Falling back to primary provider.")
        return {
            "type": "cloud_fallback",
            "model": self.llm_model,
            "base_url": self.llm_base_url
        }

    def check_compute_budget(self, session_cost: float, session_time: int) -> bool:
        """
        Enforces the compute budget.
        Returns False if the budget is exhausted.
        """
        if session_cost > self.max_cost:
            logger.warning(f"Compute budget exceeded: ${session_cost} > ${self.max_cost}")
            return False
            
        if session_time > self.max_time:
            logger.warning(f"Time budget exceeded: {session_time}s > {self.max_time}s")
            return False
            
        return True

    def load_navigator_profile(self) -> Dict[str, Any]:
        """
        Loads the local-only Navigator Profile (Anonymous Version).
        This file handles 'Public Interests' and 'Subscription Manifests'.
        """
        import yaml
        profile_path = "templates/navigator_profile.yaml"
        if not os.path.exists(profile_path):
            logger.warning(f"Navigator profile not found at {profile_path}. Using defaults.")
            return {"gossip_subscriptions": [], "knowledge_base": []}
            
        with open(profile_path, "r") as f:
            profile = yaml.safe_load(f)
            
        # Ensure node_id is updated from current identity if it's the placeholder
        if profile.get("node_id") == "0x[ED25519_PUBLIC_KEY]":
            profile["node_id"] = os.getenv("NODE_ID", "uninitialized")
            
        logger.info(f"Loaded Profile for Node {profile.get('node_id')}: {len(profile.get('gossip_subscriptions', []))} Interests active.")
        return profile
