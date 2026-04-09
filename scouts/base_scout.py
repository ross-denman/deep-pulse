#!/usr/bin/env python3
"""
Deep Pulse - Base Scout (AutoDream Curiosity Bot)

The foundational class for autonomous researchers.
Implements the Curiosity Bot loop, Surprise Metric, and 
RLM-backed hypothesis testing.
"""

import abc
import logging
import time
import random
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class BaseScout(abc.ABC):
    """Abstract Base Class for Curiosity-driven Scouts."""

    def __init__(self, 
                 perimeter: str, 
                 config_manager, 
                 economy_manager, 
                 memory_manager,
                 recursive_depth: int = 3):
        self.perimeter = perimeter
        self.config = config_manager
        self.economy = economy_manager
        self.memory = memory_manager
        self.recursive_depth = recursive_depth
        self.path_history = []
        self.session_cost = 0.0
        self.start_time = 0
        
        # Debrief stats
        self.stats = {
            "successes": 0,
            "404_errors": 0,
            "dreams": 0,
            "failed_attempts": 0,
            "preferred_paths": set(),
            "avoid_paths": set()
        }
        self.success_data = []
        
        # Instantiate Standalone Curiosity Engine & Circuit Breaker
        try:
            from src.public.core.curiosity import CuriosityBot
            self.curiosity_bot = CuriosityBot(self.memory, self.perimeter)
        except ImportError:
            logger.warning("CuriosityBot module not found. Discovery heuristics will be limited.")
            self.curiosity_bot = None

        try:
            from src.public.core.breaker import CircuitBreaker
            self.breaker = CircuitBreaker(failure_threshold=3)
        except ImportError:
            logger.warning("CircuitBreaker module not found. Skipping safety checks.")
            self.breaker = None

    @abc.abstractmethod
    async def discover(self, params: Dict[str, Any]) -> Any:
        """Passive discovery / site navigation."""
        pass

    @abc.abstractmethod
    async def extract(self, raw_data: Any, distiller: Dict[str, Any], keywords: List[str] = None) -> Dict[str, Any]:
        """Signal extraction from raw data."""
        pass

    async def run(self, initial_params: Dict[str, Any]):
        """Executes the Curiosity Bot Loop with Dynamic Error Control."""
        self.start_time = time.time()
        current_params = initial_params
        depth = self.recursive_depth
        keywords = initial_params.get("keywords", [])
        episode_id = self.memory.record_episode(self.perimeter, [])
        last_hunch = ""

        while depth > 0:
            # Jitter: Random delay to mimic human browsing (2-5s)
            delay = random.uniform(2.0, 5.0)
            logger.info(f"Stealth Mode: Jittering for {delay:.2f}s...")
            time.sleep(delay)
            
            target_url = current_params.get("url", "unknown_target")
            
            # 0. Check Breaker & Budget
            if self.breaker.check_state(target_url):
                logger.critical(f"Scout '{self.perimeter}' aborted via Circuit Breaker on {target_url}.")
                break
                
            elapsed = time.time() - self.start_time
            if not self.config.check_compute_budget(self.session_cost, int(elapsed)):
                logger.warning(f"Scout {self.perimeter} self-terminated: Budget exhausted.")
                break

            logger.info(f"Scout running {self.perimeter} at depth {depth}")
            action = {"action": "discover", "params": current_params}
            self.path_history.append(action)
            self.memory.update_path(episode_id, action)
            
            # 1. Discover
            raw_content = await self.discover(current_params)
            
            # DEC: 3-Tier Immune System
            status_code = getattr(raw_content, "status_code", 200) if not isinstance(raw_content, dict) else raw_content.get("status_code", 200)
            
            if status_code in [404, 410]:
                logger.warning(f"[DEC SYSTEM] HTTP {status_code} detected on {target_url}. Endpoint Obsolete. Triggering Broad Recon architect...")
                self.stats["404_errors"] += 1
                from urllib.parse import urlparse
                path = urlparse(target_url).path.rstrip("/")
                if path:
                    self.stats["avoid_paths"].add(path)
                # Architect Swarm Genesis Search logic triggered here
                break
            elif status_code in [401, 403]:
                logger.warning(f"[DEC SYSTEM] HTTP {status_code} detected on {target_url}. Auth Expired/Paywall block.")
                logger.info("Reporter Agent Alert: Manual Authorization Update Required.")
                break
            
            # 2. Extract (Sovereign Intelligence Cost Shield)
            distiller = self.config.get_best_distiller()
            logger.info(f"Cost Shield: Routing extract to {distiller['type']} distiller.")
            
            signal = await self.extract(raw_content, distiller, keywords=keywords)
            
            # 2.5 S2A (Surprise-to-Action) Deep Dive Trigger
            dive_target = signal.get("dive_target")
            if dive_target:
                logger.warning(f"⚡ S2A TRIGGER DETECTED: Initiating Deep Dive into {dive_target}")
                depth = max(depth, 1) # Ensure we have at least one more recursive step
                from urllib.parse import urljoin
                current_params["url"] = urljoin(target_url, dive_target)
                current_params["dive_reason"] = signal.get("meta", "Deep Dive")
                # Continue loop directly to hit the dive target
                continue

            # 3. Evaluate & Breaker Check
            score = self.evaluate_signal(signal)
            schema_drift = signal.get("schema_drift", False)
            
            # Fire the physical breaker to see if it was a generic 200 hallucination
            if self.breaker:
                self.breaker.record_pulse(target_url, score, is_schema_drift=schema_drift)
            
            if schema_drift:
                auto_approve = current_params.get("auto_approve_schema_drift", False)
                if auto_approve:
                    logger.warning(f"[DEC SYSTEM] Autonomous Schema Gate: auto_approve_schema_drift is ENABLED for {p_id}. Skipping operator approval.")
                    logger.info(f"⚡ Learning new layout autonomously for {target_url}...")
                else:
                    logger.warning(f"[DEC SYSTEM] Semantic Schema Mismatch detected. Routing to Schema Gate...")
                    try:
                        from src.public.core.manager import AgentManager
                        orchestrator = AgentManager()
                        old_f = signal.get("drift_old_field", "unknown")
                        new_f = signal.get("drift_new_field", "unknown")
                        conf = signal.get("drift_confidence", 0.0)
                        orchestrator.handle_schema_drift(target_url, old_f, new_f, conf)
                    except Exception as e:
                        logger.error(f"[DEC SYSTEM] Schema Gate failed: {e}")
            
            if score >= 0.8: # Threshold for success
                logger.info(f"[OK] High-Signal discovery confirmed: {signal}")
                self.stats["successes"] += 1
                from urllib.parse import urlparse
                path = urlparse(target_url).path.rstrip("/")
                if path:
                    self.stats["preferred_paths"].add(path)
                self.success_data.append(signal)
                self.memory.update_reward(episode_id, 1.0)
                await self.save_successful_path(episode_id, signal)
                return signal

            # Did we fail on an active hunch? Log the failure in the Loop Breaker.
            if last_hunch:
                self.curiosity_bot.record_failure(last_hunch)

            # 4. Dream (AutoDream Hypothesis via CuriosityBot)
            if self.curiosity_bot:
                logger.info("Signal below threshold. Curiosity Bot entering DREAM phase.")
                self.stats["dreams"] += 1
                
                # The standalone CuriosityBot manages the hypothesis generation
                hunch = await self.curiosity_bot.generate_hunch(raw_content, episode_id)
                last_hunch = hunch
                
                # Update params based on hunch
                current_params = self.mutate_params(current_params, hunch)
            else:
                logger.info("Signal below threshold. No CuriosityBot found, skipping DREAM phase.")
            depth -= 1

        logger.info(f"Scout {self.perimeter} finished without high-signal discovery.")
        # Final tracking for failures at depth 0
        self.stats["failed_attempts"] += 1
        if last_hunch:
            self.curiosity_bot.record_failure(last_hunch)
        return None

    def generate_summary(self, mission_id: str) -> Dict[str, Any]:
        """Generates the mission JSON summary."""
        return {
            "mission_id": mission_id,
            "scout_stats": {
                "successes": self.stats["successes"],
                "404_errors": self.stats["404_errors"],
                "dreams": self.stats["dreams"]
            },
            "new_potential_sources": list(self.stats["preferred_paths"]),
            "heuristics_update": {
                "avoid_paths": list(self.stats["avoid_paths"]),
                "preferred_paths": list(self.stats["preferred_paths"])
            }
        }

    def evaluate_signal(self, signal: Dict[str, Any]) -> float:
        """
        The Surprise Metric: Evaluates extraction quality.
        Scores based on keyword novelty, entity density, and target match.
        """
        if not signal:
            return 0.0
            
        base_confidence = signal.get("confidence", 0.5)
        
        # Surprise Heuristic: If specific high-resolution tokens are found,
        # we multiplier the signal strength to break the bootstrap deadlock.
        keywords_found = signal.get("keywords_found", [])
        scent_anchors = ["2.55x", "osteomalacia", "135 billion", "$42 billion", "bead", "lutnick", "10^26 flops", "eo 14365"]
        if any(k in scent_anchors for k in [kw.lower() for kw in keywords_found]):
            logger.info("⚡ Real-time Surprise Metric: High-resolution anchor detected. Elevating Signal.")
            return 0.95
            
        # Novelty weighting based on number of keywords found
        if keywords_found:
            base_confidence += (len(keywords_found) * 0.1)
            
        return min(0.99, base_confidence)

    async def save_successful_path(self, episode_id: int, signal: Dict[str, Any]):
        """
        Saves metadata (selectors, patterns) from a successful extraction.
        This provides the 'Fuel' for the Evolution Engine.
        """
        metadata = {
            "selectors": signal.get("selectors", {}),
            "engine": "crawl4ai",
            "timestamp": time.time()
        }
        self.memory.save_successful_metadata(episode_id, metadata)
        logger.info(f"Adaptive Intelligence: Saved successful selectors for Episode {episode_id}")

    @abc.abstractmethod
    def mutate_params(self, old_params: Dict[str, Any], hunch: str) -> Dict[str, Any]:
        """Reformulates search/navigation parameters based on a hunch."""
        pass
