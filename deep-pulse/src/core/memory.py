#!/usr/bin/env python3
"""
Deep Pulse — Memory Service (RLM Episodic Store)

Non-parametric episodic memory for scouts.
Records discovery paths (search terms, navigation, results) and 
rewards successful Signal-to-Truth paths.
"""

import sqlite3
import logging
import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class EpisodicMemory:
    """Episodic memory store for Reinforcement Learning from Memories (RLM)."""

    def __init__(self, db_path: str = "db/memory.sqlite"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initializes the SQLite episodic store."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    perimeter TEXT,
                    path_json TEXT,      -- JSON list of actions/steps
                    metadata_json TEXT,  -- JSON dict of selectors/patterns
                    reward REAL DEFAULT 0.0,
                    timestamp TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_perimeter ON episodes(perimeter)")

    def record_episode(self, perimeter: str, path: List[Dict[str, Any]]):
        """Records a new discovery path episode."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO episodes (perimeter, path_json, timestamp) VALUES (?, ?, ?)",
                (perimeter, json.dumps(path), datetime.now(timezone.utc).isoformat())
            )
            # return the row id
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def update_reward(self, entry_id: int, reward: float):
        """Updates the reward for a given episode (signal found or debunked)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE episodes SET reward = reward + ? WHERE id = ?",
                (reward, entry_id)
            )

    def retrieve_dream_paths(self, perimeter: str, limit: int = 3) -> List[List[Dict[str, Any]]]:
        """
        Retrieves high-reward discovery paths for "Dream Retrieval."
        Used by the Curiosity Bot to bias toward proven strategies.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT path_json FROM episodes WHERE perimeter = ? AND reward > 0 ORDER BY reward DESC LIMIT ?",
                (perimeter, limit)
            )
            return [json.loads(row[0]) for row in cursor.fetchall()]

    def search_similar_paths(self, query: str, limit: int = 3):
        """
        Stub for vector search.
        In the future, this will use AutoGraph-R1/MemRL with sentence-transformers.
        """
        # For MVP, we fallback to simple perimeter-based retrieval
        return self.retrieve_dream_paths(query, limit)
        
    def save_successful_metadata(self, episode_id: int, metadata: Dict[str, Any]):
        """Saves successful metadata (selectors, patterns) for an episode."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE episodes SET metadata_json = ? WHERE id = ?",
                (json.dumps(metadata), episode_id)
            )

    def log_hunch(self, entry_id: int, hunch: str):
        """Logs a curiosity bot hunch/hypothesis for an episode."""
        # For now, we append it to the metadata or a separate column if we had one.
        # Let's just log it to the console and potentially update metadata.
        logger.info(f"RLM Memory: Logging hunch for Episode {entry_id}: {hunch}")
        with sqlite3.connect(self.db_path) as conn:
            # We'll store hunches in the metadata_json for now
            cursor = conn.execute("SELECT metadata_json FROM episodes WHERE id = ?", (entry_id,))
            row = cursor.fetchone()
            metadata = json.loads(row[0]) if row and row[0] else {}
            hunches = metadata.get("hunches", [])
            hunches.append({"hunch": hunch, "timestamp": datetime.now(timezone.utc).isoformat()})
            metadata["hunches"] = hunches
            conn.execute(
                "UPDATE episodes SET metadata_json = ? WHERE id = ?",
                (json.dumps(metadata), entry_id)
            )

    def update_path(self, entry_id: int, action: Dict[str, Any]):
        """Appends a new action/step to an existing episode's path."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT path_json FROM episodes WHERE id = ?", (entry_id,))
            row = cursor.fetchone()
            path = json.loads(row[0]) if row and row[0] else []
            path.append(action)
            conn.execute(
                "UPDATE episodes SET path_json = ? WHERE id = ?",
                (json.dumps(path), entry_id)
            )

    def get_audit_candidates(self, min_reward: float = 0.8) -> List[Dict[str, Any]]:
        """
        Retrieves episodes suitable for the Evolution Engine to audit.
        Returns paths and metadata that yielded high rewards.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM episodes WHERE reward >= ? ORDER BY timestamp DESC",
                (min_reward,)
            )
            return [dict(row) for row in cursor.fetchall()]
